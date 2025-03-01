import os

def copy_files_to_output(input_dir, output_file):
    with open(output_file, 'w', encoding='utf-8') as output:
        for root, dirs, files in os.walk(input_dir):
            # 跳过包含.的隐藏文件夹
            if any(part.startswith('.') for part in root.split(os.sep)):
                continue
            for file in files:
                if file.endswith(('.html', '.py')):  # 只处理后缀为.html或.py的文件
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, input_dir)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            output.write(f"File: {relative_path}\n")
                            output.write(content)
                            output.write("\n\n")
                    except Exception as e:
                        output.write(f"Error reading {relative_path}: {e}\n\n")

if __name__ == "__main__":
    input_directory = input("请输入输入文件夹路径(input_dir): ")
    # 将output_file设置为输入文件夹路径中各部分字符串的拼接
    output_file_name = ''.join(input_directory.split(os.sep)) + "_output.txt"
    output_file = os.path.join(os.getcwd(), output_file_name)  # 将文件保存在当前工作目录
    copy_files_to_output(input_directory, output_file)
    print(f"所有符合条件的文件内容已复制到 {output_file}")