#streamlit_app.py
import streamlit as st
import requests
import json
from datetime import datetime
import streamlit.components.v1 as components

BASE_API = "http://127.0.0.1:5000/api"

def main():
    st.set_page_config(
        page_title="知识风暴",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 初始化session状态
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "login"
    if 'login_error' not in st.session_state:
        st.session_state.login_error = None
    if 'register_error' not in st.session_state:
        st.session_state.register_error = None

    # 侧边栏
    with st.sidebar:
        st.header("用户系统")
        if st.session_state.token:
            show_user_info()
            show_topic_manager()
        else:
            show_auth_forms()

    # 主内容区
    if st.session_state.token:
        show_main_content()
    else:
        st.warning("请先登录或注册")

def show_auth_forms():
    """显示认证表单"""
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        # 使用 form 的 key 确保唯一性
        login_form = st.form(key="login_form_unique_key")
        with login_form:
            username = st.text_input("用户名", key="login_username_unique")
            password = st.text_input("密码", type="password", key="login_password_unique")
            submit_button = st.form_submit_button("登录")
            
            # 调试信息直接输出到页面
            print(f"Debug - Submit状态: {submit_button}")
            print(f"Debug - 用户名: {username}, 密码长度: {len(password) if password else 0}")
            
            if submit_button:
                if username and password:
                    handle_login(username, password)
                else:
                    st.error("用户名和密码不能为空")
    with tab2:
        register_form = st.form(key="register_form_unique_key")
        with register_form:
            new_user = st.text_input("新用户名", key="register_username_unique")
            new_pass = st.text_input("新密码", type="password", key="register_password_unique")
            if st.form_submit_button("注册"):
                if new_user and new_pass:
                    handle_register(new_user, new_pass)
                else:
                    st.error("用户名和密码不能为空")

@st.cache_data(ttl=60)  # 缓存1分钟
def get_current_user():
    """获取当前登录用户信息"""
    if not st.session_state.token:
        return None
    
    try:
        # 发起带认证的API请求
        headers = {"x-access-token": st.session_state.token}
        response = requests.get(
            f"{BASE_API}/me",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
            
        # 处理过期token情况
        if response.status_code == 401:
            st.error("登录已过期，请重新登录")
            st.session_state.token = None
            st.rerun()
            
        return None
        
    except requests.exceptions.ConnectionError:
        st.error("无法连接到服务器")
        return None
    except Exception as e:
        st.error(f"获取用户信息失败: {str(e)}")
        return None


# 新增功能函数
def delete_topic(topic_id):
    """删除指定主题"""
    try:
        headers = {"x-access-token": st.session_state.token}
        response = requests.delete(
            f"{BASE_API}/topics/{topic_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            st.success("主题删除成功！")
            # 清除缓存保证数据刷新
            st.cache_data.clear()
            return True
        else:
            error_msg = response.json().get('error', '未知错误')
            st.error(f"删除失败: {error_msg}")
            return False
    except requests.exceptions.ConnectionError:
        st.error("无法连接到服务器")
        return False
    except Exception as e:
        st.error(f"请求异常: {str(e)}")
        return False

def get_sessions(topic_id):
    """获取指定主题的会话列表"""
    try:
        headers = {"x-access-token": st.session_state.token}
        response = requests.get(
            f"{BASE_API}/topics/{topic_id}/sessions",
            headers=headers
        )
        
        if response.status_code == 200:
            return sorted(response.json(), 
                         key=lambda x: x['created_at'], 
                         reverse=True)
        return []
    except requests.exceptions.ConnectionError:
        st.error("无法连接到服务器")
        return []
    except Exception as e:
        st.error(f"获取会话失败: {str(e)}")
        return []

def logout():
    """安全退出登录"""
    # 清除所有相关session状态
    keys_to_clear = ['token', 'current_user', 'selected_topic', 'selected_session']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # 强制刷新页面
    st.experimental_rerun()

def show_user_info():
    """显示用户信息"""
    try:
        user_info = get_current_user()
        if user_info:
            st.success(f"欢迎，{user_info['username']}")
            if st.button("退出登录", key="logout_btn"):
                logout()
        else:
            st.error("登录状态异常")
            logout()
    except Exception as e:
        st.error(f"状态获取失败: {str(e)}")
        logout()

def create_topic(topic_name, args):
    """创建新主题"""
    try:
        headers = {"x-access-token": st.session_state.token}
        response = requests.post(
            f"{BASE_API}/topics",
            json={
                "name": topic_name,
                "args": args
            },
            headers=headers
        )
        
        if response.status_code == 201:
            st.success("主题创建成功！")
            # 清除主题缓存
            st.cache_data.clear()
            return True
        else:
            error_msg = response.json().get('message', '未知错误')
            st.error(f"主题创建失败: {error_msg}")
            return False
    except requests.exceptions.ConnectionError:
        st.error("无法连接到服务器")
        return False
    except Exception as e:
        st.error(f"请求异常: {str(e)}")
        return False

def show_topic_manager():
    """主题管理侧边栏"""
    st.header("主题管理")
    
    # 新建主题
    with st.expander("新建研究主题", expanded=False):
        with st.form("new_topic_form"):
            name = st.text_input("主题名称")
            # 修正参数键名与RunnerArgument对应
            args = {
                "retriever": st.selectbox("搜索引擎", ["bing", "you", "brave", "serper", "duckduckgo", "tavily", "searxng", "semantic"], index=1),
                "retrieve_top_k": st.slider("检索结果数量", 5, 20, 5),
                "max_search_queries": st.number_input("最大搜索查询数", 1, 10, 2),
                "total_conv_turn": st.number_input("最大对话轮数", 5, 50, 20),
                "max_search_thread": st.number_input("检索器的最大并行线程数", 1, 20, 5),
                "max_search_queries_per_turn": st.number_input("每轮对话中考虑的最大搜索查询数", 1, 10, 3),
                "warmstart_max_num_experts": st.number_input("热启动期间，观点引导 QA 中的专家最大数量", 1, 10, 3),
                "warmstart_max_turn_per_experts": st.number_input("热启动期间，每个专家的最大对话轮数", 1, 10, 2),
                "warmstart_max_thread": st.number_input("热启动期间，用于并行观点引导 QA 的最大线程数", 1, 10, 3),
                "max_thread_num": st.number_input("使用的最大线程数", 1, 20, 5),
                "max_num_round_table_experts": st.number_input("圆桌讨论中活跃专家的最大数量", 1, 10, 2),
                "moderator_override_N_consecutive_answering_turn": st.number_input("在主持人覆盖对话之前，连续的专家回答轮数", 1, 10, 3),
                "node_expansion_trigger_count": st.number_input("触发节点扩展的节点包含超过 N 个片段", 1, 20, 10),
                "enable_log_print": st.checkbox("启用控制台日志打印", value=True)
            }

            if st.form_submit_button("创建主题"):
                if create_topic(name, args):
                    st.experimental_rerun()
    
    # 显示已有主题
    st.subheader("现有主题")
    topics = get_topics()
    for topic in topics:
        col1, col2 = st.columns([4,1])
        with col1:
            st.markdown(f"**{topic['name']}**")
            st.caption(f"创建时间: {topic.get('created_at', '未知时间')}")
        with col2:
            if st.button("🗑️", key=f"del_{topic['id']}"):
                st.session_state[f'confirm_delete_{topic["id"]}'] = True
            
            if st.session_state.get(f'confirm_delete_{topic["id"]}', False):
                st.error("⚠️ 确定要永久删除该主题吗？")
                
                # 使用水平排列的按钮（侧边栏兼容方案）
                confirm_clicked = st.button(
                    "✔️ 确认删除", 
                    key=f"conf_del_{topic['id']}",
                    type="primary"
                )
                cancel_clicked = st.button(
                    "✖️ 取消", 
                    key=f"cancel_del_{topic['id']}"
                )
                
                if confirm_clicked:
                    if delete_topic(topic['id']):
                        del st.session_state[f'confirm_delete_{topic["id"]}']
                        st.experimental_rerun()
                if cancel_clicked:
                    del st.session_state[f'confirm_delete_{topic["id"]}']
                    st.experimental_rerun()

def show_main_content():
    """主内容区"""
    st.header("协作研究会话")
    
    # 会话选择
    selected_topic = st.selectbox(
        "选择研究主题",
        get_topics(),
        format_func=lambda x: x['name']
    )
    
    if selected_topic:
        sessions = get_sessions(selected_topic['id'])
        if sessions:
            selected_session = st.selectbox(
                "选择会话",
                sessions,
                format_func=lambda x: f"{x['created_at'][:10]} | 对话数: {x['message_count']} | 最后消息: {x['last_message'][:20]}..."
            )
            print('Line 289:',selected_session)
            show_session_interface(selected_session)
        else:
            if st.button("新建会话"):
                create_session(selected_topic['id'])
                st.experimental_rerun()

def show_session_interface(session):
    """整合后的会话界面"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 对话历史区
        st.subheader("研究对话")
        messages = get_messages(session['session_id'])
        for msg in messages:
            with st.chat_message("user" if msg['role'] == 'user' else "assistant"):
                st.markdown(f"**{msg['role'].capitalize()}**: {msg['content']}")
                st.caption(msg['timestamp'])
        
        # 输入功能区
        input_col1, input_col2 = st.columns([3, 1])
        with input_col1:
            user_input = st.text_input("输入你的想法或问题...", key=f"input_{session['session_id']}")
        with input_col2:
            if st.button("🚀 发送", key=f"send_{session['session_id']}"):
                if user_input:
                    send_message(session['session_id'], user_input)
                    st.rerun()
                else:
                    st.warning("请输入内容")
            if st.button("⚡ 自动推进", key=f"auto_{session['session_id']}"):
                auto_step(session['session_id'])
                st.rerun()
    
    with col2:
        # 控制面板
        st.subheader("控制面板")
        if st.button("📄 生成报告", key=f"report_{session['session_id']}"):
            report = generate_report(session['session_id'])
            st.markdown(report['content'])
        
        if st.button("🔄 重置会话", key=f"reset_{session['session_id']}"):
            if reset_session(session['session_id']):
                st.rerun()
        
        # 知识图谱预览
        st.subheader("知识图谱")
        if st.button("🔄 刷新图谱", key=f"kg_refresh_{session['session_id']}"):
            visualize_knowledge_graph(session['session_id'])

def handle_login(username, password):
    """处理登录请求"""
    print(f"Debug: handle_login called with username: {username}")  # 添加调试信息
    if not username or not password:
        st.error("用户名和密码不能为空")
        return
        
    try:
        print("Sending login request...")  # 保留现有的调试信息
        response = requests.post(
            f"{BASE_API}/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            st.session_state.token = response.json()['token']
            st.session_state.login_error = None
            st.rerun()
        else:
            st.session_state.login_error = response.json().get('message', '未知错误')
            st.error(f"登录失败: {st.session_state.login_error}")
    except Exception as e:
        st.session_state.login_error = f"连接服务器失败: {str(e)}"
        st.error(f"登录失败: {st.session_state.login_error}")

def handle_register(username, password):
    try:
        response = requests.post(
            f"{BASE_API}/register",
            json={"username": username, "password": password}
        )
        print("Line 188 response.status_code:",response.status_code)
        if response.status_code == 201:
            st.session_state.register_success = True
            st.session_state.active_tab = "login"
            st.rerun()
        else:
            st.session_state.register_error = response.json().get('message', '未知错误')
            st.error(f"注册失败: {st.session_state.register_error}")
            # st.rerun()
    except Exception as e:
        st.session_state.register_error = f"连接服务器失败: {str(e)}"
        st.error(f"注册失败: {st.session_state.register_error}")

def get_topics():
    """获取主题列表"""
    try:
        headers = {"x-access-token": st.session_state.token}
        response = requests.get(f"{BASE_API}/topics", headers=headers)
        return response.json() if response.ok else []
    except requests.exceptions.ConnectionError:
        st.error("无法连接到服务器")
        return []
    except Exception as e:
        st.error(f"获取主题列表失败: {str(e)}")
        return []

def create_session(topic_id):
    headers = {"x-access-token": st.session_state.token}
    response = requests.post(
        f"{BASE_API}/sessions",
        json={"topic_id": topic_id},
        headers=headers
    )
    if response.status_code != 201:
        st.error("创建会话失败")

def auto_step(session_id):
    headers = {"x-access-token": st.session_state.token}
    response = requests.post(
        f"{BASE_API}/sessions/{session_id}/step",
        json={"observation": True},
        headers=headers
    )
    return response.json() if response.ok else None

def get_messages(session_id):
    """获取指定会话的消息历史"""
    try:
        headers = {"x-access-token": st.session_state.token}
        response = requests.get(
            f"{BASE_API}/sessions/{session_id}/messages",
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"获取消息失败: {response.json().get('message', '未知错误')}")
            return []
    except requests.exceptions.ConnectionError:
        st.error("无法连接到服务器")
        return []
    except Exception as e:
        st.error(f"获取消息异常: {str(e)}")
        return []

# def visualize_knowledge_graph(session_id):
#     """知识图谱可视化"""
#     try:
#         graph_data = requests.get(f"{BASE_API}/sessions/{session_id}/knowledge_graph").json()
#         # 使用graphviz或类似库渲染
#         st.graphviz_chart(render_graph(graph_data))
#     except Exception as e:
#         st.error(f"图谱加载失败: {str(e)}")

def send_message(session_id, content):
    """发送用户消息到服务器"""
    try:
        headers = {
            "x-access-token": st.session_state.token,
            "Content-Type": "application/json"
        }
        response = requests.post(
            f"{BASE_API}/sessions/{session_id}/step",
            headers=headers,
            json={"input": content}
        )
        
        if response.status_code == 201:
            st.cache_data.clear()  # 清除消息缓存
            return True
        else:
            error_msg = response.json().get('error', '未知错误')
            st.error(f"消息发送失败: {error_msg}")
            return False
    except requests.exceptions.ConnectionError:
        st.error("无法连接到服务器")
        return False
    except Exception as e:
        st.error(f"请求异常: {str(e)}")
        return False

def generate_report(session_id):
    """调用API生成会话报告并显示"""
    headers = {"x-access-token": st.session_state.token}
    response = requests.post(
        f"{BASE_API}/sessions/{session_id}/report",
        headers=headers
    )
    if response.status_code == 200:
        report_data = response.json()
        st.success("报告生成成功！")
        return report_data
    else:
        error_msg = response.json().get('error', '未知错误')
        st.error(f"生成报告失败: {error_msg}")
        return None

if __name__ == "__main__":
    main()