# app.py
from flask import Flask, jsonify, request, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import uuid
import json
from functools import wraps
from flask_cors import CORS
from knowledge_storm.collaborative_storm.engine import (
    CollaborativeStormLMConfigs,
    RunnerArgument,
    CoStormRunner,
    LoggingWrapper
)
from knowledge_storm.collaborative_storm.modules.callback import LocalConsolePrintCallBackHandler
from knowledge_storm.utils import load_api_key
import types
import os
from knowledge_storm.lm import OpenAIModel, AzureOpenAIModel, LitellmModel
from knowledge_storm.rm import (
    YouRM, BingSearch, BraveRM, SerperRM,
    DuckDuckGoSearchRM, TavilySearchRM, SearXNG, SemanticScholarRM
)
from sqlalchemy.exc import SQLAlchemyError
from flask_socketio import SocketIO, emit


app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///knowledge_storm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app, cors_allowed_origins="*")

# 数据库模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    topics = db.relationship('Topic', backref='user', lazy=True)

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sessions = db.relationship('Session', backref='topic', lazy=True)
    args = db.Column(db.Text)  # 存储序列化的运行参数

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), unique=True, nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    runner_state = db.Column(db.Text)  # 存储序列化的CoStormRunner状态
    messages = db.relationship('Message', backref='session', lazy=True)
    reports = db.relationship('Report', backref='session', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    msg_type = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'role': self.role,
            'msg_type': self.msg_type,
            'timestamp': self.timestamp.isoformat()
        } 

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)

# 辅助函数
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/api/topics/<int:topic_id>', methods=['DELETE'])
@token_required
def delete_topic_endpoint(current_user, topic_id):
    """删除主题及其所有相关数据"""
    topic = Topic.query.filter_by(id=topic_id, user_id=current_user.id).first()
    if not topic:
        return jsonify({'error': 'Topic not found'}), 404
    
    try:
        # 级联删除所有关联数据
        db.session.delete(topic)
        db.session.commit()
        return jsonify({'message': 'Topic deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/topics/<int:topic_id>/sessions', methods=['GET'])
@token_required
def get_topic_sessions(current_user, topic_id):
    """获取指定主题的所有会话"""
    topic = Topic.query.filter_by(id=topic_id, user_id=current_user.id).first()
    if not topic:
        return jsonify({'error': 'Topic not found'}), 404
    
    sessions = []
    for session in topic.sessions:
        sessions.append({
            'id': session.id,
            'session_id': session.session_id,
            'created_at': session.messages[0].timestamp.isoformat() if session.messages else None,
            'message_count': len(session.messages),
            'last_message': session.messages[-1].content if session.messages else None
        })
    return jsonify(sessions), 200

@app.after_request
def add_security_headers(response):
    """添加安全头防止状态残留"""
    response.headers['Cache-Control'] = 'no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def configure_lm_models():
    """配置所有语言模型"""
    # 导入LitellmModel
    from knowledge_storm.lm import LitellmModel
    
    # 设置模型名称
    gpt_4o_model_name = 'gpt-4o-mini'
    
    # 配置模型参数
    openai_kwargs = {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "api_provider": "openai",
        "temperature": 1.0,
        "top_p": 0.9,
        "api_base": os.getenv("OPENAI_API_BASE"),
    }
    
    # 初始化各模块语言模型
    lm_config = CollaborativeStormLMConfigs()
    
    # 创建各个模型实例
    question_answering_lm = LitellmModel(model=gpt_4o_model_name, max_tokens=1000, **openai_kwargs)
    discourse_manage_lm = LitellmModel(model=gpt_4o_model_name, max_tokens=500, **openai_kwargs)
    utterance_polishing_lm = LitellmModel(model=gpt_4o_model_name, max_tokens=2000, **openai_kwargs)
    warmstart_outline_gen_lm = LitellmModel(model=gpt_4o_model_name, max_tokens=500, **openai_kwargs)
    question_asking_lm = LitellmModel(model=gpt_4o_model_name, max_tokens=300, **openai_kwargs)
    knowledge_base_lm = LitellmModel(model=gpt_4o_model_name, max_tokens=1000, **openai_kwargs)
    
    # 设置各个模型到配置中
    lm_config.set_question_answering_lm(question_answering_lm)
    lm_config.set_discourse_manage_lm(discourse_manage_lm)
    lm_config.set_utterance_polishing_lm(utterance_polishing_lm)
    lm_config.set_warmstart_outline_gen_lm(warmstart_outline_gen_lm)
    lm_config.set_question_asking_lm(question_asking_lm)
    lm_config.set_knowledge_base_lm(knowledge_base_lm)
    
    return lm_config


def get_retriever(runner_argument, retriever_type="you"):
    """根据类型获取检索器实例"""
    print('Warning: retriever_type is deprecated, please use runner_argument.retriever instead!!!!!')
    retriever_map = {
        'bing': lambda: BingSearch(bing_search_api=os.getenv('BING_SEARCH_API_KEY'), k=runner_argument.retrieve_top_k),
        'you': lambda: YouRM(ydc_api_key=os.getenv('YDC_API_KEY'), k=runner_argument.retrieve_top_k),
        'brave': lambda: BraveRM(brave_search_api_key=os.getenv('BRAVE_API_KEY'), k=runner_argument.retrieve_top_k),
        'duckduckgo': lambda: DuckDuckGoSearchRM(k=runner_argument.retrieve_top_k, safe_search='On', region='us-en'),
        'serper': lambda: SerperRM(serper_search_api_key=os.getenv('SERPER_API_KEY'), query_params={'num': runner_argument.retrieve_top_k}),
        'tavily': lambda: TavilySearchRM(tavily_search_api_key=os.getenv('TAVILY_API_KEY'), k=runner_argument.retrieve_top_k),
        'searxng': lambda: SearXNG(searxng_api_key=os.getenv('SEARXNG_API_KEY'), k=runner_argument.retrieve_top_k),
        'semantic': lambda: SemanticScholarRM(semantic_scholar_api_key=os.getenv('SEMANTIC_SCHOLAR_API_KEY'), k=runner_argument.retrieve_top_k)
    }

    # 确保retriever_type是字符串
    retriever_key = str(retriever_type).strip("()',")
    if retriever_key not in retriever_map:
        raise ValueError(f"不支持的检索器类型: {retriever_key}，可选值: {list(retriever_map.keys())}")
    return retriever_map[retriever_key]()

def restore_runner_state(runner_state):
    """恢复CoStormRunner状态"""
    # 加载API密钥配置
    load_api_key(toml_file_path='.config/secrets.toml')
    data = json.loads(runner_state)
    runner_argument = RunnerArgument.from_dict(data["runner_argument"])
    rm = get_retriever(runner_argument)
    return CoStormRunner.from_dict(json.loads(runner_state), lm_config=configure_lm_models(), rm=rm)

def initialize_runner(args_dict, topic_name):
    """根据参数初始化CoStormRunner"""
    
    # 加载API密钥配置
    load_api_key(toml_file_path='.config/secrets.toml')
    
    # 初始化语言模型配置
    lm_config = configure_lm_models()
    
    # 创建RunnerArgument配置
    runner_argument = RunnerArgument(
        topic=topic_name,
        retrieve_top_k=args_dict.get("retrieve_top_k", 10),
        max_search_queries=args_dict.get("max_search_queries", 3),
        total_conv_turn=args_dict.get("total_conv_turn", 20),
        max_search_thread=args_dict.get("max_search_thread", 5),
        max_search_queries_per_turn=args_dict.get("max_search_queries_per_turn", 3),
        warmstart_max_num_experts=args_dict.get("warmstart_max_num_experts", 3),
        warmstart_max_turn_per_experts=args_dict.get("warmstart_max_turn_per_experts", 2),
        warmstart_max_thread=args_dict.get("warmstart_max_thread", 3),
        max_thread_num=args_dict.get("max_thread_num", 10),
        max_num_round_table_experts=args_dict.get("max_num_round_table_experts", 2),
        moderator_override_N_consecutive_answering_turn=args_dict.get("moderator_override_N_consecutive_answering_turn", 3),
        node_expansion_trigger_count=args_dict.get("node_expansion_trigger_count", 10)
    )

    # 获取检索器
    rm = get_retriever(runner_argument, args_dict.get("retriever", "you"))

    # 创建Runner实例
    runner = CoStormRunner(
        lm_config=lm_config,
        runner_argument=runner_argument,
        logging_wrapper=LoggingWrapper(lm_config),
        rm=rm,
        callback_handler=LocalConsolePrintCallBackHandler() if args_dict.get("enable_log_print", False) else None
    )
    
    # 执行热启动
    runner.warm_start()
    return runner

@app.route('/api/me', methods=['GET'])
@token_required
def get_current_user_endpoint(current_user):
    return jsonify({
        'user_id': current_user.id,
        'username': current_user.username#,
        # 'created_at': current_user.date_created.isoformat()
    })

# 用户认证API
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists!'}), 409
        
    hashed_password = generate_password_hash(data['password'])
    new_user = User(username=data['username'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'Registered successfully!'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials!'}), 401
        
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'])
    
    return jsonify({'token': token})

# 主题管理API
@app.route('/api/topics', methods=['POST'])
@token_required
def create_topic(current_user):
    data = request.json
    new_topic = Topic(
        name=data['name'],
        user_id=current_user.id,
        args=json.dumps(data.get('args', {})))
    db.session.add(new_topic)
    db.session.commit()
    return jsonify({'message': 'Topic created', 'id': new_topic.id}), 201

@app.route('/api/topics', methods=['GET'])
@token_required
def get_topics(current_user):
    topics = Topic.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'args': json.loads(t.args)
    } for t in topics])

# 会话管理API
@app.route('/api/sessions', methods=['POST'])
@token_required
def create_session(current_user):
    data = request.json
    topic = Topic.query.filter_by(id=data['topic_id'], user_id=current_user.id).first()
    if not topic:
        return jsonify({'error': 'Topic not found'}), 404
    
    # 初始化知识风暴运行器
    args_dict = json.loads(topic.args)
    runner = initialize_runner(args_dict, topic.name)
    
    # 创建新会话
    new_session = Session(
        session_id=str(uuid.uuid4()),
        topic_id=topic.id,
        runner_state=json.dumps(runner.to_dict())
    )
    db.session.add(new_session)
    
    # 保存初始消息
    init_message = Message(
        content=f"New session started for topic: {topic.name}",
        role="system",
        msg_type="notification",
        session=new_session
    )
    db.session.add(init_message)
    db.session.commit()
    
    return jsonify({
        'session_id': new_session.session_id,
        'topic_id': topic.id
    }), 201

# 消息处理API
@app.route('/api/sessions/<session_id>/step', methods=['POST'])
@token_required
def process_step(current_user, session_id):
    session = Session.query.filter_by(session_id=session_id).first()
    if not session or session.topic.user_id != current_user.id:
        return jsonify({'error': 'Session not found'}), 404
    
    # 加载运行器状态
    runner = restore_runner_state(session.runner_state)
    
    # 处理用户输入
    data = request.json
    user_input = data.get('input', '')
    observation_mode = data.get('observation', False)
    
    if user_input:
        # 保存用户消息
        user_msg = Message(
            content=user_input,
            role="user",
            msg_type="text",
            session=session
        )
        db.session.add(user_msg)
        runner.step(user_utterance=user_input)
    
    # 执行下一步
    if observation_mode:
        conv_turn = runner.step()
    else:
        conv_turn = runner.step()
    
    # 保存系统消息
    system_msg = Message(
        content=conv_turn.utterance,
        role=conv_turn.role,
        msg_type="text",
        session=session
    )
    db.session.add(system_msg)
    
    # 更新运行器状态
    session.runner_state = json.dumps(runner.to_dict())
    db.session.commit()
    
    return jsonify({
        'response': conv_turn.utterance,
        'role': conv_turn.role
    })

# 报告生成API
@app.route('/api/sessions/<session_id>/report', methods=['POST'])
@token_required
def generate_report(current_user, session_id):
    session = Session.query.filter_by(session_id=session_id).first()
    if not session or session.topic.user_id != current_user.id:
        return jsonify({'error': 'Session not found'}), 404
    
    # 加载运行器状态
    runner = restore_runner_state(session.runner_state)
    
    # 生成报告
    # print('Line 165:',runner.knowledge_base)
    runner.knowledge_base.reorganize()
    report_content = runner.generate_report()
    
    # 保存报告
    new_report = Report(
        content=report_content,
        session=session
    )
    db.session.add(new_report)
    db.session.commit()
    
    return jsonify({
        'report_id': new_report.id,
        'content': report_content
    })

@app.route('/api/sessions/<session_id>/messages', methods=['GET'])
@token_required
def get_session_messages(current_user, session_id):
    """获取指定会话的所有消息"""
    # 验证会话归属
    session = Session.query.filter_by(session_id=session_id).first()
    print('Line 408:',session)
    print('Line 409:',current_user.id)
    if not session or session.topic.user_id != current_user.id:
        return jsonify({'error': 'Session not found or access denied'}), 404
    
    try:
        # 获取按时间排序的消息列表
        messages = Message.query.filter_by(session_id=session.id)\
                      .order_by(Message.timestamp.asc()).all()
        
        # 构建响应数据
        messages_data = [{
            'id': msg.id,
            'role': msg.role,
            'content': msg.content,
            'msg_type': msg.msg_type,
            'timestamp': msg.timestamp.isoformat()
        } for msg in messages]
        
        return jsonify(messages_data), 200
    
    except SQLAlchemyError as e:
        app.logger.error(f"Database error: {str(e)}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# @app.route('/api/sessions/<session_id>/messages', methods=['POST'])
# @token_required
# def send_message(current_user, session_id):
#     """处理用户消息并生成回复"""
#     data = request.json
#     print('Line 438:',data)
#     if not data or 'content' not in data:
#         return jsonify({'error': 'Invalid message data'}), 400
    
#     # 验证会话归属
#     session = Session.query.filter_by(session_id=session_id).first()
#     print('Line 445:',session,current_user)
#     if not session or session.topic.user_id != current_user.id:
#         return jsonify({'error': 'Session not found or access denied'}), 404
    
#     try:
#         # 保存用户消息
#         user_msg = Message(
#             content=data['content'],
#             role='user',
#             msg_type='text',
#             session_id=session.id
#         )
#         db.session.add(user_msg)
        
#         # 获取关联的runner状态
#         runner = restore_runner_state(session.runner_state)
        
#         # 处理用户输入
#         runner.step(user_utterance=data['content'])
#         response = runner.step()
        
#         # 保存AI回复
#         ai_msg = Message(
#             content=response.utterance,
#             role=response.role,
#             msg_type=getattr(response, 'msg_type', 'text'),
#             session_id=session.id
#         )
#         db.session.add(ai_msg)
        
#         # 更新runner状态
#         session.runner_state = json.dumps(runner.get_state())
        
#         db.session.commit()
        
#         # 通过WebSocket广播消息
#         socketio.emit('new_message', {
#             'session_id': session_id,
#             'user_message': user_msg.to_dict(),
#             'ai_message': ai_msg.to_dict()
#         })
        
#         return jsonify({'status': 'success'}), 201
    
#     except SQLAlchemyError as e:
#         db.session.rollback()
#         app.logger.error(f"Database error: {str(e)}")
#         return jsonify({'error': 'Failed to save message'}), 500
#     except Exception as e:
#         app.logger.error(f"Processing error: {str(e)}")
#         return jsonify({'error': 'Message processing failed'}), 500

@app.route('/api/sessions/<session_id>/reports', methods=['GET'])
@token_required
def get_session_reports(current_user, session_id):
    """获取指定会话的所有报告"""
    session = Session.query.filter_by(session_id=session_id).first()
    if not session or session.topic.user_id != current_user.id:
        return jsonify({'error': 'Session not found or access denied'}), 404
    
    reports = Report.query.filter_by(session_id=session.id)\
               .order_by(Report.created_at.desc()).all()
    
    return jsonify([{
        'id': report.id,
        'content': report.content,
        'created_at': report.created_at.isoformat()
    } for report in reports]), 200

if __name__ == '__main__':
    app.run(port=5000)#,debug=True)