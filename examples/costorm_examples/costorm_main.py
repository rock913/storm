import os
import json
import shutil
from argparse import ArgumentParser
from knowledge_storm.collaborative_storm.engine import (
    CollaborativeStormLMConfigs,
    RunnerArgument,
    CoStormRunner
)
from knowledge_storm.collaborative_storm.modules.callback import LocalConsolePrintCallBackHandler
from knowledge_storm.lm import OpenAIModel, AzureOpenAIModel
from knowledge_storm.logging_wrapper import LoggingWrapper
from knowledge_storm.rm import (
    YouRM,
    BingSearch,
    BraveRM,
    SerperRM,
    DuckDuckGoSearchRM,
    TavilySearchRM,
    SearXNG,
    SemanticScholarRM
)
from knowledge_storm.utils import load_api_key

# import logging

# # 设置日志配置
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("debug.log"),
#         logging.StreamHandler()
#     ]
# )

DEMO_WORKING_DIR = "DEMO_WORKING_DIR"

def setup_working_directory():
    """
    Create DEMO_WORKING_DIR in the current directory if it doesn't exist.
    """
    current_dir = os.getcwd()
    print(f"当前工作目录: {current_dir}")
    if not os.path.exists(DEMO_WORKING_DIR):
        os.makedirs(DEMO_WORKING_DIR)
        print(f"创建工作目录: {DEMO_WORKING_DIR}")
    else:
        print(f"工作目录已存在: {DEMO_WORKING_DIR}")

def list_existing_topics():
    """
    List all existing topic directories within DEMO_WORKING_DIR.
    """
    topics = [
        name for name in os.listdir(DEMO_WORKING_DIR)
        if os.path.isdir(os.path.join(DEMO_WORKING_DIR, name))
    ]
    return topics

def choose_topic():
    """
    Allow the user to choose to load an existing topic or create a new one.
    Returns the topic name and its corresponding directory path.
    """
    topics = list_existing_topics()
    print("\n=== 主题选择 ===")
    if topics:
        print("1. 加载已有主题")
        print("2. 创建新主题")
        choice = input("请选择操作 (1/2): ").strip()
        if choice == '1':
            print("\n已有主题列表:")
            for idx, topic in enumerate(topics, 1):
                print(f"{idx}. {topic}")
            selected = input("请输入要加载的主题编号: ").strip()
            if selected.isdigit() and 1 <= int(selected) <= len(topics):
                topic = topics[int(selected)-1]
                topic_dir = os.path.join(DEMO_WORKING_DIR, topic)
                print(f"已加载主题: {topic}")
                return topic, topic_dir
            else:
                print("无效的选择。")
                return choose_topic()
        elif choice == '2':
            topic = input("请输入新主题名称: ").strip()
            if not topic:
                print("主题名称不能为空。")
                return choose_topic()
            topic_dir = os.path.join(DEMO_WORKING_DIR, topic)
            if os.path.exists(topic_dir):
                print("该主题已存在，请选择加载已有主题或输入其他名称。")
                return choose_topic()
            os.makedirs(topic_dir)
            print(f"已创建新主题目录: {topic_dir}")
            return topic, topic_dir
        else:
            print("无效的选择。")
            return choose_topic()
    else:
        print("当前没有任何主题，创建一个新主题。")
        topic = input("请输入新主题名称: ").strip()
        if not topic:
            print("主题名称不能为空。")
            return choose_topic()
        topic_dir = os.path.join(DEMO_WORKING_DIR, topic)
        os.makedirs(topic_dir)
        print(f"已创建新主题目录: {topic_dir}")
        return topic, topic_dir

def load_runner_state(topic_dir, lm_config):
    """
    Load the runner state from instance_dump.json if it exists.
    """
    instance_dump_path = os.path.join(topic_dir, "instance_dump.json")
    if os.path.exists(instance_dump_path):
        with open(instance_dump_path, "r") as f:
            instance_data = json.load(f)
        runner = CoStormRunner.from_dict(instance_data, lm_config=lm_config)
        print("已加载之前的会话状态。")
        return runner
    else:
        print("没有找到之前的会话状态，将开始新的会话。")
        return None

def save_runner_state(topic_dir, runner):
    """
    Save the runner state to instance_dump.json.
    """
    instance_dump_path = os.path.join(topic_dir, "instance_dump.json")
    with open(instance_dump_path, "w") as f:
        json.dump(runner.to_dict(), f, indent=2)
    print("已保存会话状态。")

def initialize_runner(args, topic):
    """
    Initialize the Co-STORM runner with the given arguments and topic.
    """
    load_api_key(toml_file_path='.config/secrets.toml')
    lm_config = CollaborativeStormLMConfigs()
    openai_kwargs = {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "api_provider": "openai",
        "temperature": 1.0,
        "top_p": 0.9,
        "api_base": os.getenv("OPENAI_API_BASE"),
    } if os.getenv('OPENAI_API_TYPE') == 'openai' else {
        "api_key": os.getenv("AZURE_API_KEY"),
        "temperature": 1.0,
        "top_p": 0.9,
        "api_base": os.getenv("AZURE_API_BASE"),
        "api_version": os.getenv("AZURE_API_VERSION"),
    }

    ModelClass = OpenAIModel if os.getenv('OPENAI_API_TYPE') == 'openai' else AzureOpenAIModel

    gpt_4o_mini_model_name = 'gpt-4o-mini'
    gpt_4o_model_name = 'gpt-4o-mini' #'gpt-4o'
    print("I am using: ",gpt_4o_model_name)
    if os.getenv('OPENAI_API_TYPE') == 'azure':
        openai_kwargs['api_base'] = os.getenv('AZURE_API_BASE')
        openai_kwargs['api_version'] = os.getenv('AZURE_API_VERSION')

    question_answering_lm = ModelClass(model=gpt_4o_model_name, max_tokens=1000, **openai_kwargs)
    discourse_manage_lm = ModelClass(model=gpt_4o_model_name, max_tokens=500, **openai_kwargs)
    utterance_polishing_lm = ModelClass(model=gpt_4o_model_name, max_tokens=2000, **openai_kwargs)
    warmstart_outline_gen_lm = ModelClass(model=gpt_4o_model_name, max_tokens=500, **openai_kwargs)
    question_asking_lm = ModelClass(model=gpt_4o_model_name, max_tokens=300, **openai_kwargs)
    knowledge_base_lm = ModelClass(model=gpt_4o_model_name, max_tokens=1000, **openai_kwargs)

    lm_config.set_question_answering_lm(question_answering_lm)
    lm_config.set_discourse_manage_lm(discourse_manage_lm)
    lm_config.set_utterance_polishing_lm(utterance_polishing_lm)
    lm_config.set_warmstart_outline_gen_lm(warmstart_outline_gen_lm)
    lm_config.set_question_asking_lm(question_asking_lm)
    lm_config.set_knowledge_base_lm(knowledge_base_lm)

    # Prepare runner arguments
    runner_argument = RunnerArgument(
        topic=topic,
        retrieve_top_k=args.retrieve_top_k,
        max_search_queries=args.max_search_queries,
        total_conv_turn=args.total_conv_turn,
        max_search_thread=args.max_search_thread,
        max_search_queries_per_turn=args.max_search_queries_per_turn,
        warmstart_max_num_experts=args.warmstart_max_num_experts,
        warmstart_max_turn_per_experts=args.warmstart_max_turn_per_experts,
        warmstart_max_thread=args.warmstart_max_thread,
        max_thread_num=args.max_thread_num,
        max_num_round_table_experts=args.max_num_round_table_experts,
        moderator_override_N_consecutive_answering_turn=args.moderator_override_N_consecutive_answering_turn,
        node_expansion_trigger_count=args.node_expansion_trigger_count
    )

    logging_wrapper = LoggingWrapper(lm_config)
    callback_handler = LocalConsolePrintCallBackHandler() if args.enable_log_print else None

    # Initialize retriever
    retriever_map = {
        'bing': BingSearch,
        'you': YouRM,
        'brave': BraveRM,
        'duckduckgo': DuckDuckGoSearchRM,
        'serper': SerperRM,
        'tavily': TavilySearchRM,
        'searxng': SearXNG,
        'semantic': SemanticScholarRM
    }

    retriever_key = args.retriever
    if retriever_key not in retriever_map:
        raise ValueError(f'Invalid retriever: {retriever_key}. Choose from {list(retriever_map.keys())}')

    if retriever_key == 'bing':
        rm = BingSearch(bing_search_api=os.getenv('BING_SEARCH_API_KEY'), k=runner_argument.retrieve_top_k)
    elif retriever_key == 'you':
        rm = YouRM(ydc_api_key=os.getenv('YDC_API_KEY'), k=runner_argument.retrieve_top_k)
    elif retriever_key == 'brave':
        rm = BraveRM(brave_search_api_key=os.getenv('BRAVE_API_KEY'), k=runner_argument.retrieve_top_k)
    elif retriever_key == 'duckduckgo':
        rm = DuckDuckGoSearchRM(k=runner_argument.retrieve_top_k, safe_search='On', region='us-en')
    elif retriever_key == 'serper':
        rm = SerperRM(serper_search_api_key=os.getenv('SERPER_API_KEY'), query_params={'autocorrect': True, 'num': 10, 'page': 1})
    elif retriever_key == 'tavily':
        rm = TavilySearchRM(tavily_search_api_key=os.getenv('TAVILY_API_KEY'), k=runner_argument.retrieve_top_k, include_raw_content=True)
    elif retriever_key == 'searxng':
        rm = SearXNG(searxng_api_key=os.getenv('SEARXNG_API_KEY'), k=runner_argument.retrieve_top_k)
    elif retriever_key == 'semantic':
        rm = SemanticScholarRM(semantic_scholar_api_key=os.getenv('SEMANTIC_SCHOLAR_API_KEY'), k=runner_argument.retrieve_top_k)
    else:
        raise ValueError(f'Unsupported retriever: {retriever_key}')

    runner = CoStormRunner(
        lm_config=lm_config,
        runner_argument=runner_argument,
        logging_wrapper=logging_wrapper,
        rm=rm,
        callback_handler=callback_handler
    )

    # Warm start the system
    runner.warm_start()

    return runner

def generate_report_and_save(topic_dir, runner):
    """
    Generate the final report and save all necessary files.
    """
    # 确保主题目录存在
    os.makedirs(topic_dir, exist_ok=True)
    
    # 重新组织知识库并生成报告
    runner.knowledge_base.reorganize()
    article = runner.generate_report()

    # 保存报告
    report_path = os.path.join(topic_dir, "report.md")
    with open(report_path, "w", encoding='utf-8') as f:
        f.write(article)
    print(f"已生成报告并保存至: {report_path}")

    # 保存会话状态
    save_runner_state(topic_dir, runner)

    # 保存日志
    log_dump = runner.dump_logging_and_reset()
    log_path = os.path.join(topic_dir, "log.json")
    with open(log_path, "w", encoding='utf-8') as f:
        json.dump(log_dump, f, indent=2, ensure_ascii=False)
    print(f"已保存日志至: {log_path}")

def interactive_conversation(runner, topic_dir):
    """
    Interactive loop allowing the user to observe, inject, save, or exit.
    """
    print("\n=== 进入交互式对话模式 ===")
    while True:
        print("\n请选择操作:")
        print("1. 观察代理发言")
        print("2. 注入用户发言")
        print("3. 更新并保存结果")
        print("4. 退出")
        choice = input("请输入操作编号 (1/2/3/4): ").strip()

        if choice == '1':
            conv_turn = runner.step()
            print("Line 287: costorm_main: conv_turn:",conv_turn)
            print(f"\n**{conv_turn.role}**: {conv_turn.utterance}\n")
        elif choice == '2':
            user_utterance = input("请输入您的发言: ").strip()
            if user_utterance:
                runner.step(user_utterance=user_utterance)
                print("已注入您的发言。")
            else:
                print("发言不能为空。")
        elif choice == '3':
            generate_report_and_save(topic_dir, runner)
        elif choice == '4':
            confirm = input("是否要保存当前会话状态并退出? (y/n): ").strip().lower()
            if confirm == 'y':
                generate_report_and_save(topic_dir, runner)
                print("已退出会话。")
                break
            else:
                print("未保存会话状态。")
                break
        else:
            print("无效的选择，请重新输入。")

def main(args):
    # Step 1: Setup working directory
    setup_working_directory()

    # Step 2: Choose or create a topic
    topic, topic_dir = choose_topic()

    # Step 3: Initialize or load runner
    lm_config = CollaborativeStormLMConfigs()
    runner = initialize_runner(args, topic)

    # Step 4: Load existing runner state if available
    existing_runner = load_runner_state(topic_dir, lm_config)
    if existing_runner:
        runner = existing_runner
    else:
        # If new session, ask for initial steps
        print("\n=== 开始新的会话 ===")
        # Optionally, you can perform initial steps here
        pass

    # Step 5: Enter interactive conversation loop
    interactive_conversation(runner, topic_dir)

if __name__ == '__main__':
    parser = ArgumentParser(description="基于Co-STORM的交互式工具")
    # global arguments
    parser.add_argument('--retriever', type=str, choices=['bing', 'you', 'brave', 'serper', 'duckduckgo', 'tavily', 'searxng','semantic'],
                        default='you',
                        help='选择用于信息检索的搜索引擎 API。')
    # hyperparameters for co-storm
    parser.add_argument(
        '--retrieve_top_k',
        type=int,
        default=10,
        help='在检索器中为每个查询检索的前 k 个结果。'
    )
    parser.add_argument(
        '--max_search_queries',
        type=int,
        default=2,
        help='每个问题考虑的最大搜索查询数量。'
    )
    parser.add_argument(
        '--total_conv_turn',
        type=int,
        default=20,
        help='对话的最大轮数。'
    )
    parser.add_argument(
        '--max_search_thread',
        type=int,
        default=5,
        help='检索器的最大并行线程数。'
    )
    parser.add_argument(
        '--max_search_queries_per_turn',
        type=int,
        default=3,
        help='每轮对话中考虑的最大搜索查询数。'
    )
    parser.add_argument(
        '--warmstart_max_num_experts',
        type=int,
        default=3,
        help='热启动期间，观点引导 QA 中的专家最大数量。'
    )
    parser.add_argument(
        '--warmstart_max_turn_per_experts',
        type=int,
        default=2,
        help='热启动期间，每个专家的最大对话轮数。'
    )
    parser.add_argument(
        '--warmstart_max_thread',
        type=int,
        default=3,
        help='热启动期间，用于并行观点引导 QA 的最大线程数。'
    )
    parser.add_argument(
        '--max_thread_num',
        type=int,
        default=5,
        help=("使用的最大线程数。"
              "如果在调用 LM API 时持续收到 'Exceed rate limit' 错误，请考虑减少此值。")
    )
    parser.add_argument(
        '--max_num_round_table_experts',
        type=int,
        default=2,
        help='圆桌讨论中活跃专家的最大数量。'
    )
    parser.add_argument(
        '--moderator_override_N_consecutive_answering_turn',
        type=int,
        default=3,
        help=('在主持人覆盖对话之前，连续的专家回答轮数。')
    )
    parser.add_argument(
        '--node_expansion_trigger_count',
        type=int,
        default=10,
        help='触发节点扩展的节点包含超过 N 个片段。'
    )

    # Boolean flags
    parser.add_argument(
        '--enable_log_print',
        action='store_true',
        help='如果设置，则启用控制台日志打印。'
    )

    args = parser.parse_args()
    main(args)
