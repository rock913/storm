#streamlit_app.py
import streamlit as st
import requests
import json
from datetime import datetime
import streamlit.components.v1 as components
import traceback
import os

BASE_API = "http://127.0.0.1:5000/api"

# 新增自定义CSS样式
def inject_custom_css():
    st.markdown(f"""
    <style>
        /* 主容器 */
        .main {{
            background: #f5f7fb;
            padding: 2rem;
        }}

        /* 响应式边栏 */
        @media (max-width: 768px) {{
            .sidebar .sidebar-content {{
                width: 100%;
                transform: translateX(-100%);
                transition: transform 300ms ease-out;
            }}
            .sidebar--open .sidebar-content {{
                transform: translateX(0);
            }}
        }}

        /* 卡片式布局 */
        .card {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}

        /* 现代按钮样式 */
        .stButton>button {{
            border-radius: 8px;
            padding: 0.5rem 1rem;
            transition: all 0.2s;
        }}
        .stButton>button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}

        /* 输入框增强 */
        .stTextInput>div>div>input {{
            border-radius: 8px;
            padding: 0.75rem;
        }}
    </style>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="知识风暴",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 新增配置：禁用文件监视
    os.environ["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "false"
    
    inject_custom_css()
    
    # 初始化session状态
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'mobile_menu_open' not in st.session_state:
        st.session_state.mobile_menu_open = False
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "login"
    if 'login_error' not in st.session_state:
        st.session_state.login_error = None
    if 'register_error' not in st.session_state:
        st.session_state.register_error = None

    # 响应式布局容器
    with st.container():
        # 移动端菜单切换按钮
        if st.session_state.token:
            cols = st.columns([1, 10, 1])
            with cols[0]:
                if st.button("☰", key="mobile_menu_toggle"):
                    st.session_state.mobile_menu_open = not st.session_state.mobile_menu_open
            with cols[1]:
                # 动态显示当前主题名称
                current_topic = next((t for t in get_topics() if t['id'] == st.session_state.get("selected_topic_id")), None)
                display_text = current_topic['name'] if current_topic else "知识风暴"
                st.header(f"🌪️ {display_text}", anchor=False)

        # 修复后的响应式边栏
        if st.session_state.mobile_menu_open:
            with st.sidebar:
                if st.session_state.token:
                    render_sidebar_content()
                else:
                    show_auth_forms()
        else:
            with st.sidebar:
                if st.session_state.token:
                    render_sidebar_content()
                else:
                    show_auth_forms()

        # 主内容区
        if st.session_state.token:
            render_main_content()
        else:
            st.warning("请先登录或注册")

def render_sidebar_content():
    """响应式边栏内容"""
    with st.container():
        # LOGO展示
        st.markdown("""
        <div style="text-align: center; margin: 20px 0;">
            <h1 style="font-size: 24px; color: #2c3e50;">🌪️ 知识风暴</h1>
        </div>
        """, unsafe_allow_html=True)

        # 新建主题（折叠状态）
        with st.expander("➕ 新建研究主题", expanded=False):
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
                if st.form_submit_button("创建"):
                    if create_topic(name, args):
                        st.rerun()

        # 现有主题列表样式优化
        topics = get_topics()
        if topics:
            with st.container(height=300):
                st.markdown("""
                <style>
                    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
                        gap: 0.2rem !important;
                    }
                    div[data-testid="stButton"] {
                        margin: 2px 0;
                    }
                </style>
                """, unsafe_allow_html=True)
                
                for topic in topics:
                    is_selected = st.session_state.get("selected_topic_id") == topic['id']
                    btn_label = f"📌 {topic['name']}"
                    
                    if st.button(
                        btn_label,
                        key=f"topic_{topic['id']}",
                        use_container_width=True,
                        type="primary" if is_selected else "secondary",
                        help=f"点击切换至主题：{topic['name']}"
                    ):
                        st.session_state.selected_topic_id = topic['id']
                        st.rerun()
        else:
            st.info("点击上方新建主题开始研究")

        # 我的信息（默认折叠）
        with st.expander("👤 我的信息", expanded=False):
            user_info = get_current_user()
            if user_info:
                st.markdown(f"""
                **{user_info['username']}**  
                📅 注册时间: {user_info.get('created_at', '未知时间')}
                """)
                if st.button("🚪 退出登录", use_container_width=True):
                    logout()

def render_main_content():
    """现代布局主内容区"""
    selected_topic_id = st.session_state.get("selected_topic_id")
    
    if not selected_topic_id:
        st.info("请先在侧边栏选择研究主题")
        return
    
    # 移除原有的标题展示代码
    # 直接进入选项卡布局
    tab1, tab2 = st.tabs(["💬 研究对话", "📄 生成文章"])
    
    with tab1:
        render_chat_interface(selected_topic_id)
    
    with tab2:
        render_article_interface(selected_topic_id)

def render_chat_interface(topic_id):
    """简化后的聊天界面"""
    # 获取当前主题的会话列表
    sessions = get_sessions(topic_id)
    
    if not sessions:
        if st.button("✨ 新建会话", use_container_width=True):
            create_session(topic_id)
            st.rerun()
        return
    
    # 默认显示最新会话
    selected_session = sessions[0]
    
    # 会话操作区
    # with st.container():
    #     col1, col2 = st.columns([1, 3])
    #     with col1:
    #         if st.button("🔄 刷新会话", key="refresh_session"):
    #             st.rerun()
    #     with col2:
    #         if st.button("⚡ 自动推进对话", key="auto_progress"):
    #             auto_step(selected_session['session_id'])
    #             st.rerun()
    
    # 显示会话消息
    show_session_messages(selected_session)

def render_article_interface(topic_id):
    """文章生成界面优化版"""
    sessions = get_sessions(topic_id)
    
    if not sessions:
        st.warning("请先创建至少一个会话")
        return
    
    # 自动选择最新会话
    selected_session = sessions[0]
    
    with st.container():
        # 获取已有报告
        existing_reports = get_session_reports(selected_session['session_id'])
        latest_report = existing_reports[0] if existing_reports else None

        # 生成/重新生成按钮
        if st.button("🔄 重新生成文章" if latest_report else "📄 生成文章", 
                    use_container_width=True,
                    type="primary" if latest_report else "secondary"):
            with st.spinner("正在生成研究报告..."):
                report_data = generate_report(selected_session['session_id'])
                if report_data:
                    st.session_state.current_article = {
                        'content': report_data['content']
                    }
                    st.rerun()
        
        # 显示最新报告内容
        if latest_report:
            # 分割正文和参考文献
            content_part, refs_part = split_content_and_references(latest_report['content'])
            
            # 解析引用
            citations = parse_citations(refs_part)
            
            # 显示带链接的正文
            linked_content = link_citations(content_part, citations)
            st.markdown(linked_content, unsafe_allow_html=True)
            # print('content_part:',content_part[:1500])
            # print('refs_part:',refs_part[:1500])
            # print('citations:',citations)
            # print('linked_content:',linked_content[:1500])
            
            # 显示格式化参考文献
            if citations:
                st.markdown("---\n**参考文献**")
                for idx, ref in citations.items():
                    st.markdown(f"""
                    <div style="margin: 8px 0; line-height: 1.5">
                        <sup>[{idx}]</sup> 
                        <a href="{ref['url']}" target="_blank" style="text-decoration: none; color: #2c3e50;">
                            {ref['title']}
                        </a>
                        <br>
                        <span style="color: #666; font-size: 0.9em">{ref['snippet']}</span>
                    </div>
                    """, unsafe_allow_html=True)
        elif 'current_article' in st.session_state:
            st.markdown(st.session_state.current_article['content'])

def validate_credentials(username: str, password: str) -> tuple[bool, str]:
    """验证用户凭据"""
    if not username or not password:
        return False, "用户名和密码不能为空"
    if len(password) < 6:
        return False, "密码长度至少需要6个字符"
    return True, ""

def show_auth_forms():
    """显示认证表单"""
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录")
            
            if submitted:
                print(f"Line 350 username: {username}")
                is_valid, error_msg = validate_credentials(username, password)
                
                if not is_valid:
                    st.error(error_msg)
                else:
                    try:
                        # 添加请求头验证
                        headers = {"Content-Type": "application/json"}
                        response = requests.post(
                            f"{BASE_API}/login",
                            json={"username": username, "password": password},
                            headers=headers,
                            timeout=5
                        )

                        if response.status_code == 200:
                            if 'token' in response.json():
                                st.session_state.token = response.json()['token']
                                st.success("登录凭证有效")
                                # 添加token验证步骤
                                validate_response = requests.get(
                                    f"{BASE_API}/me",
                                    headers={"x-access-token": st.session_state.token}
                                )
                                if validate_response.status_code == 200:
                                    st.rerun()
                                else:
                                    st.error("Token验证失败")
                            else:
                                st.error("响应中缺少token字段")
                        else:
                            error_data = response.json()
                            st.error(f"认证失败: {error_data.get('message', '未知错误')}")

                    except requests.exceptions.JSONDecodeError:
                        st.error("服务器返回了非JSON响应")
                        print(f"⚠️ 非JSON响应内容: {response.text}")
                    except Exception as e:
                        st.error(f"网络请求异常: {str(e)}")

        # if not st.session_state.token:
        #     st.info("请输入用户名和密码后点击登录按钮")

    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("新用户名")
            new_password = st.text_input("新密码", type="password")
            confirm_password = st.text_input("确认密码", type="password")
            register_submit = st.form_submit_button("注册")
            
            if register_submit:
                is_valid, error_msg = validate_credentials(new_username, new_password)
                if not is_valid:
                    st.error(error_msg)
                elif new_password != confirm_password:
                    st.error("两次输入的密码不一致")
                else:
                    handle_register(new_username, new_password)

@st.cache_data(ttl=10)  # 缓存1分钟
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

def show_topic_manager():
    """主题管理侧边栏"""
    st.header("主题管理")
    
    # 新建主题（移除嵌套的expander）
    with st.container():
        st.subheader("新建研究主题")
        with st.form("new_topic_form"):
            name = st.text_input("主题名称")
            
            # 将参数配置放入带滚动条的容器
            with st.container(height=400):  # 固定高度容器
                # 修正参数键名与RunnerArgument对应
                args = {
                    "retriever": st.selectbox("搜索引擎", ["bing", "you", "brave", "serper", "duckduckgo", "tavily", "searxng", "semantic"], index=1),
                    "retrieve_top_k": st.slider("检索结果数量", 5, 20, 5),
                    "max_search_queries": st.number_input("最大搜索查询数", 1, 10, 2),
                    "total_conv_turn": st.number_input("最大对话轮数", 5, 50, 20),
                    "max_search_thread": st.number_input("检索线程数", 1, 20, 5,
                                                       help="同时进行检索的最大线程数量"),
                    "max_search_queries_per_turn": st.number_input("每轮搜索查询数", 1, 10, 3),
                    "warmstart_max_num_experts": st.number_input("初始专家数量", 1, 10, 3,
                                                              help="热启动阶段的专家数量"),
                    "warmstart_max_turn_per_experts": st.number_input("专家对话轮数", 1, 10, 2),
                    "warmstart_max_thread": st.number_input("初始线程数", 1, 10, 3),
                    "max_thread_num": st.number_input("总线程数", 1, 20, 5),
                    "max_num_round_table_experts": st.number_input("圆桌专家数", 1, 10, 2),
                    "moderator_override_N_consecutive_answering_turn": st.number_input("主持人接管阈值", 1, 10, 3,
                                                                                   help="连续对话轮数超过该值后主持人接管"),
                    "node_expansion_trigger_count": st.number_input("节点扩展阈值", 1, 20, 10),
                    "enable_log_print": st.checkbox("启用日志打印", value=True)
                }

            # 将提交按钮放在滚动容器外
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

def handle_register(username, password):
    try:
        response = requests.post(
            f"{BASE_API}/register",
            json={"username": username, "password": password}
        )
        print("Line 188 response.status_code:",response.status_code)
        if response.status_code == 201:
            st.success("注册成功！请返回登录页面进行登录。")
        else:
            st.error(f"注册失败: {response.json().get('message', '未知错误')}")
    except Exception as e:
        st.error(f"连接服务器失败: {str(e)}")

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

def show_session_messages(session):
    """优化后的对话界面布局"""
    if not session:
        return
    
    try:
        # 消息显示区域（增加底部间距）
        with st.container(height=520, border=False):
            messages = get_messages(session['session_id'])
            for msg in messages:
                # 根据消息角色设置不同的样式
                if msg['role'] == 'user':
                    with st.chat_message('user'):
                        st.markdown(msg['content'])
                elif msg['role'] == 'system':
                    with st.chat_message('assistant', avatar='🤖'):
                        st.markdown(msg['content'])
                elif msg['role'] == 'moderator':
                    with st.chat_message('assistant', avatar='👨‍💼'):
                        st.markdown(msg['content'])
                elif msg['role'] == 'expert':
                    with st.chat_message('assistant', avatar='👨‍🔬'):
                        st.markdown(msg['content'])
                else:
                    with st.chat_message('assistant'):
                        st.markdown(msg['content'])
                
                # 显示时间戳
                st.caption(f"发送时间: {msg['timestamp'][:19]}")

        # 操作按钮与输入区域融合
        with st.container():
            # 第一行：紧凑型自动推进按钮
            auto_col, _ = st.columns([0.3, 0.7])
            with auto_col:
                if st.button("⏩ 自动推进", 
                            key=f"auto_step_{session['session_id']}",
                            use_container_width=True,
                            help="自动执行下一步对话流程"):
                    auto_step(session['session_id'])
                    st.rerun()

            # 第二行：融合式输入区域
            input_col, btn_col = st.columns([0.85, 0.15])
            with input_col:
                user_input = st.text_input(
                    "输入消息",
                    key=f"msg_input_{session['session_id']}",
                    placeholder="输入消息内容...",
                    label_visibility="collapsed",
                )
            with btn_col:
                send_btn = st.button(
                    "🚀",  # 使用图标代替文字
                    key=f"send_btn_{session['session_id']}", 
                    use_container_width=True,
                    help="发送消息",
                    type="primary"
                )
                if send_btn and user_input:
                    if send_message(session['session_id'], user_input):
                        st.rerun()

        # 添加自定义样式
        st.markdown("""
        <style>
            /* 输入框圆角效果 */
            div[data-testid="stTextInput"] input {
                border-radius: 20px !important;
                padding-right: 20px !important;
            }
            /* 按钮对齐优化 */
            div[data-testid="column"]:has(> div[data-testid="stVerticalBlock"] > button) {
                align-items: end;
            }
        </style>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"加载消息失败: {str(e)}")

def get_messages(session_id):
    """获取会话消息"""
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

# 新增获取报告函数
@st.cache_data(ttl=10)
def get_session_reports(session_id):
    """获取指定会话的报告列表"""
    try:
        headers = {"x-access-token": st.session_state.token}
        response = requests.get(
            f"{BASE_API}/sessions/{session_id}/reports",
            headers=headers
        )
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        st.error(f"获取报告失败: {str(e)}")
        return []

# 新增引用解析函数
def split_content_and_references(content):
    """分割正文和参考文献部分"""
    ref_start = content.find("参考文献")
    if ref_start == -1:
        return content, ""
    return content[:ref_start], content[ref_start:]

def parse_citations(refs_part):
    """解析新版参考文献条目"""
    import re
    citations = {}
    # 更新正则表达式匹配新格式
    pattern = r'\[(\d+)\] \[(.*?)\]\((https?://\S+)\)\s*\n\*(.*?)\*'
    
    matches = re.finditer(pattern, refs_part, re.DOTALL)
    for match in matches:
        idx = match.group(1)
        title = match.group(2).strip()
        url = match.group(3).strip()
        snippet = match.group(4).replace('\n', ' ').strip()
        
        # 处理多行标题的情况
        clean_title = re.sub(r'\s+', ' ', title).replace('[PDF] ', '')
        
        citations[idx] = {
            "title": clean_title,
            "url": url,
            "snippet": snippet
        }
    return citations

def link_citations(content, citations):
    """将正文中的[数字]转为可点击的弹出式引用"""
    import re
    pattern = r'\[(\d+)\]'
    
    def replace_match(match):
        idx = match.group(1)
        if idx in citations:
            return f'<sup><a href="{citations[idx]["url"]}" target="_blank" style="text-decoration: none; color: #2c3e50;">[{idx}]</a></sup>'
        return match.group(0)
    
    return re.sub(pattern, replace_match, content)

if __name__ == "__main__":
    main()