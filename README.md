# CLIScript - 命令行界面脚本语言

一个用于构建CLI应用程序的领域特定语言，旨在替代复杂的argparse配置，通过简洁的声明式语法定义命令行界面。

## 特性

- 🚀 **声明式语法** - 简洁直观的命令定义
- 🔧 **类型安全** - 内置类型系统和验证
- 📚 **模块化** - 支持导入Python模块和函数
- 🌳 **结构化命令** - 支持子命令、根选项和默认命令
- ⚡ **自动生成** - 自动生成帮助信息和参数解析

## 快速开始

### 安装

```bash
pip install cliscript
```

### 基本语法

```cliscript
# 定义应用名称
appname "文件管理器"

# 导入功能模块
use "file_tools.py"

# 定义根选项（全局选项）
root -v, --version [bool] [default:false] "显示版本信息" -> show_version()
root -h, --help [bool] [default:false] "显示帮助信息" -> show_help()

# 定义命令
cmd copy "复制文件和目录"
  -r, --recursive [bool] [default:false] "递归复制"
  -f, --force [bool] [default:false] "覆盖已存在文件"
  <source> [string] [required] "源文件路径"
  <target> [string] [required] "目标文件路径"
  -> file_tools.copy($source, $target, $recursive, $force)
```

### 完整示例

```cliscript
appname "高级文件管理器"
use "cli_utils.py"

# 全局选项
root -v, --version [bool] [default:false] "显示版本信息" -> show_version()
root --config <path> [string] [default:./config.json] "配置文件路径" -> load_config($path)

# 文件操作命令
cmd copy "复制文件或目录"
  -r, --recursive [bool] [default:false] "递归复制目录"
  -f, --force [bool] [default:false] "强制覆盖"
  -p, --preserve [bool] [default:false] "保留文件属性"
  <source> [string] [required] "源路径"
  <target> [string] [required] "目标路径"
  -> file_utils.copy($source, $target, $recursive, $force, $preserve)

cmd move "移动文件或目录"
  -f, --force [bool] [default:false] "强制覆盖"
  <source> [string] [required] "源路径"
  <target> [string] [required] "目标路径"
  -> file_utils.move($source, $target, $force)

cmd delete "删除文件或目录"
  -r, --recursive [bool] [default:false] "递归删除目录"
  -f, --force [bool] [default:false] "强制删除"
  <path> [string] [required] "要删除的路径"
  -> file_utils.delete($path, $recursive, $force)

# 搜索命令
cmd find "查找文件"
  -n, --name <pattern> [string] [required] "文件名模式"
  -t, --type <filetype> [choice:file,dir,symlink] [default:file] "文件类型"
  -s, --size <size> [string] "文件大小条件"
  <directory> [string] [default:.] "搜索目录"
  -> search_utils.find_files($directory, $name, $type, $size)

cmd grep "在文件中搜索文本"
  -i, --ignore-case [bool] [default:false] "忽略大小写"
  -r, --recursive [bool] [default:false] "递归搜索"
  -n, --line-number [bool] [default:false] "显示行号"
  <pattern> [string] [required] "搜索模式"
  <file...> [string] [required] "要搜索的文件"
  -> search_utils.grep($pattern, $file, $ignore_case, $recursive, $line_number)

# 系统信息命令
cmd info "显示系统信息"
  -d, --detail <level> [int] [default:1] "详细信息级别"
  -f, --format <format> [choice:json,yaml,table] [default:table] "输出格式"
  -> system_utils.get_info($detail, $format)

# 默认命令（当没有指定子命令时执行）
default "显示帮助信息或执行默认操作"
  -l, --list [bool] [default:false] "列出所有命令"
  -> show_default_help($list)
```

## 语法详解

### 数据类型

CLIScript 支持以下数据类型：

- `[bool]` - 布尔值 (`true`/`false`)
- `[string]` - 字符串
- `[int]` - 整数
- `[float]` - 浮点数
- `[choice:value1,value2,...]` - 枚举值

### 属性

- `[required]` - 必需的参数
- `[default:value]` - 默认值
- `[multiple]` - 允许多个值（用于可变参数）

### 特殊语法

- `<arg...>` - 可变参数（接受多个值）
- `-> function($param1, $param2)` - 执行Python函数
- `$variable` - 引用参数值

## Python 模块示例

对应的Python模块应该包含CLIScript中引用的函数：

```python
# cli_utils.py
class file_utils:
    @staticmethod
    def copy(source, target, recursive=False, force=False, preserve=False):
        """复制文件或目录的实现"""
        print(f"复制: {source} -> {target}")
        print(f"递归: {recursive}, 强制: {force}, 保留属性: {preserve}")
        # 实际的文件复制逻辑
        return f"成功复制 {source} 到 {target}"
    @staticmethod
    def move(source, target, force=False):
        """移动文件或目录的实现"""
        print(f"移动: {source} -> {target}")
        print(f"强制: {force}")
        # 实际的文件移动逻辑
        return f"成功移动 {source} 到 {target}"
    @staticmethod
    def delete(path, recursive=False, force=False):
        """删除文件或目录的实现"""
        print(f"删除: {path}")
        print(f"递归: {recursive}, 强制: {force}")
        # 实际的文件删除逻辑
        return f"成功删除 {path}"
    @staticmethod
    def show_version():
        """显示版本信息"""
        return "高级文件管理器 v2.1.0"
    @staticmethod
    def load_config(path):
        """加载配置文件"""
        return f"加载配置文件: {path}"
    @staticmethod
    def show_default_help(list_commands=False):
        """显示默认帮助"""
        if list_commands:
            return "可用命令: copy, move, delete, find, grep, info"
        else:
            return "使用 --help 查看帮助信息或 --list 查看命令列表"

class search_utils:
    @staticmethod
    def find_files(directory, name_pattern, file_type="file", size_condition=None):
        """查找文件的实现"""
        print(f"在 {directory} 中查找文件")
        print(f"模式: {name_pattern}, 类型: {file_type}, 大小: {size_condition}")
        # 实际的文件搜索逻辑
        return f"找到匹配的文件"
    @staticmethod
    def grep(pattern, files, ignore_case=False, recursive=False, line_number=False):
        """文本搜索的实现"""
        print(f"搜索模式: {pattern}")
        print(f"文件: {files}")
        print(f"忽略大小写: {ignore_case}, 递归: {recursive}, 行号: {line_number}")
        # 实际的文本搜索逻辑
        return f"找到匹配的文本"

class system_utils:
    @staticmethod
    def get_info(detail_level=1, output_format="table"):
        """获取系统信息的实现"""
        print(f"详细信息级别: {detail_level}")
        print(f"输出格式: {output_format}")
        # 实际的系统信息获取逻辑
        return "系统信息摘要"
```

## 使用方法

### 1. 创建CLIScript文件

创建 `file_manager.cli` 文件，包含上述CLIScript代码。

### 2. 创建Python主程序

```python
# main.py
from CLIScript.script.core import CLIScriptParser
from CLIScript.cli import CLIRunner
import sys

def main():
    # 读取CLIScript文件
    with open('file_manager.cli', 'r', encoding='utf-8') as f:
        source = f.read()
    
    # 解析CLIScript
    parser = CLIScriptParser()
    result = parser.parse(source)
    
    # 运行CLI
    runner = CLIRunner(result["ast"])
    runner.run()

if __name__ == "__main__":
    main()
```

### 3. 运行命令

```bash
# 显示版本信息
python main.py --version

# 显示帮助
python main.py --help

# 复制文件
python main.py copy -rf source.txt target.txt

# 查找文件
python main.py find -n "*.py" -t file src/

# 搜索文本
python main.py grep -ir "function" *.py

# 系统信息
python main.py info -d 2 -f json
```

## 相比传统argparse

**传统argparse方式:**
```python
import argparse

parser = argparse.ArgumentParser(description='文件管理器')
subparsers = parser.add_subparsers(dest='command')

# copy命令
copy_parser = subparsers.add_parser('copy', help='复制文件')
copy_parser.add_argument('-r', '--recursive', action='store_true', help='递归复制')
copy_parser.add_argument('-f', '--force', action='store_true', help='强制覆盖')
copy_parser.add_argument('source', help='源文件')
copy_parser.add_argument('target', help='目标文件')

# move命令  
move_parser = subparsers.add_parser('move', help='移动文件')
move_parser.add_argument('-f', '--force', action='store_true', help='强制覆盖')
move_parser.add_argument('source', help='源文件')
move_parser.add_argument('target', help='目标文件')

# ... 更多命令和重复代码
```

**CLIScript方式:**
```cliscript
cmd copy "复制文件"
  -r, --recursive [bool] [default:false] "递归复制"
  -f, --force [bool] [default:false] "强制覆盖"
  <source> [string] [required] "源文件"
  <target> [string] [required] "目标文件"
  -> file_utils.copy($source, $target, $recursive, $force)

cmd move "移动文件"
  -f, --force [bool] [default:false] "强制覆盖"
  <source> [string] [required] "源文件"
  <target> [string] [required] "目标文件"
  -> file_utils.move($source, $target, $force)
```

