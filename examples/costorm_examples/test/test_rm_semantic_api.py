import os
from knowledge_storm.rm import SemanticScholarRM
from knowledge_storm.utils import load_api_key

load_api_key(toml_file_path='../.config/secrets.toml')

# 初始化SemanticScholarRM检索器
semantic_scholar_rm = SemanticScholarRM(
    semantic_scholar_api_key=os.getenv('SEMANTIC_SCHOLAR_API_KEY'),
    k=3,
    # is_valid_source=lambda url: "arxiv.org" in url or "doi.org" in url
)

# 执行查询
results = semantic_scholar_rm.forward("ai agent")

# 输出结果
for result in results:
    print(f"Title: {result['title']}")
    print(f"URL: {result['url']}")
    print(f"Description: {result['description']}")
    print(f"Snippets: {result['snippets']}")
    print(f"Meta: {result['meta']}")
    print("-" * 40)
print('Results：',len(results))
# 获取并重置使用量
usage = semantic_scholar_rm.get_usage_and_reset()
print(f"API Usage: {usage}")
