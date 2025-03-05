# Co-STORM 知识协作研究平台

![示例截图](demo_screenshot.png) <!-- 请根据实际添加截图 -->

## 项目概述

基于Co-STORM框架构建的知识协作研究平台，结合多智能体对话系统和知识管理功能。前端使用Streamlit构建交互界面，后端采用Flask框架提供RESTful API，实现以下核心功能：

- 🧑💻 多角色AI研究者协同对话
- 🔍 集成多种搜索引擎的知识检索
- 📚 研究主题与会话的持久化管理
- 📊 自动生成结构化研究报告
- 🔐 基于JWT的用户认证系统

## 主要功能

### 用户系统
- 用户注册/登录
- JWT令牌认证
- 个人资料管理

### 研究管理
- 主题创建/加载/删除
- 参数化研究配置（搜索引擎选择、检索参数设置）
- 会话历史追溯

### 协作研究
- 多智能体实时对话
- 用户干预与对话引导
- 知识库动态更新

### 成果输出
- Markdown格式研究报告生成
- 会话过程记录与回放
- 知识片段溯源管理

## 技术栈

| 类别         | 技术组件                                                                 |
|--------------|--------------------------------------------------------------------------|
| 后端框架     | Flask + Flask-SQLAlchemy + Flask-Migrate                                |
| 前端框架     | Streamlit                                                               |
| 数据库       | SQLite (开发环境) / 支持PostgreSQL等生产级数据库                          |
| 语言模型     | GPT-4o-mini (通过LiteLLM集成)                                            |
| 搜索引擎     | Bing/You.com/Brave/Serper/DuckDuckGo等                                  |
| 辅助工具     | JWT认证、Werkzeug密码哈希、CORS支持                                      |

## 部署流程

### 1. 环境准备

1. 克隆仓库

```bash
git clone https://github.com/your_username/storm.git
cd storm/examples/costorm_examples
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置文件

```bash
cp .config/secrets_example.toml .config/secrets.toml
vim .config/secrets.toml # 填写实际API密钥
```

### 3. 数据库初始化

```bash
flask db init
flask db migrate
flask db upgrade
```

### 4. 启动后端服务

```bash
# 开发模式 (默认端口5000)
python app.py
# 生产模式建议使用gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 5. 启动前端界面

```bash
streamlit run streamlit_app.py
```

## 配置说明

### 关键配置文件

`.config/secrets.toml`

```toml
OPENAI_API_KEY = "your_openai_key" # OpenAI API密钥
BING_SEARCH_API_KEY = "your_bing_key" # Bing搜索API密钥
SEMANTIC_SCHOLAR_API_KEY = "your_s2_key" # 学术论文API密钥
CORE_API_KEY = "your_core_key" # CORE学术资源API
```

### 可选配置
- 修改数据库配置：`app.py`中`SQLALCHEMY_DATABASE_URI`
- 调整后端端口：`app.py`末尾`app.run(port=5000)`
- 前端配置：`streamlit_app.py`中`BASE_API`地址

## 注意事项

1. **依赖管理**：建议使用Python虚拟环境
2. **API密钥**：需自行申请各服务API密钥
3. **并发请求**：开发环境SQLite可能遇到并发问题，生产环境建议使用PostgreSQL
4. **文件权限**：确保数据库文件`instance/app.db`有写入权限

## Docker 部署方案

###  部署命令

启动开发环境：
```bash
# 初始化数据库
docker-compose run --rm backend flask db upgrade

# 启动所有服务
docker compose up -d
```

生产环境部署：
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```


### 6. 访问服务
- 前端界面：http://localhost:8501
- 后端API：http://localhost:5000
- 数据库管理：可通过pgAdmin等工具连接至`db:5432`

### 方案特点
1. **环境隔离**：每个服务独立容器化
2. **数据持久化**：PostgreSQL数据持久存储
3. **配置分离**：通过环境变量管理敏感信息
4. **扩展性**：支持多节点部署
5. **开发/生产一致性**：通过compose文件区分环境

### 更新策略
```bash
# 更新代码后重新构建
docker compose build
# 滚动更新
docker compose up -d --force-recreate
```

### 注意事项
1. 首次启动需执行数据库迁移
2. 生产环境需配置HTTPS
3. 建议使用 secrets 管理敏感信息
4. 调整资源限制（CPU/MEM）根据实际需求
