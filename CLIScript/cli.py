import argparse
import sys
import importlib
from typing import Dict, List, Any, Callable


class CLIRunner:
    """CLI运行器 - 基于AST直接执行CLI命令"""

    def __init__(self, ast: List[Dict[str, Any]]):
        self.ast = ast
        self.imported_modules = {}
        self.parser = None
        self.subparsers = None
        self.has_default_command = False
        self.default_command = None
        self.appname = "CLI Tool"
        self.root_options = []  # 存储根选项
        self.root_actions = {}  # 存储根选项对应的动作

    def run(self):
        """运行CLI"""
        try:
            # 导入模块
            self._import_modules()

            # 检查是否有default命令
            self._check_default_command()

            # 查找appname
            self._find_appname()

            # 查找根选项
            self._find_root_options()

            # 构建解析器
            self._build_parser()

            # 解析参数并执行命令
            self._execute_command()

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    def _find_appname(self):
        """查找并设置应用名称"""
        for node in self.ast:
            if node["type"] == "appname":
                self.appname = node["name"]
                break

    def _import_modules(self):
        """导入use语句中指定的模块"""
        for node in self.ast:
            if node["type"] == "use":
                module_name = node["module"].replace('.py', '')
                try:
                    module = importlib.import_module(module_name)
                    self.imported_modules[module_name] = module
                except ImportError as e:
                    print(f"Error: Could not import module {module_name}: {e}", file=sys.stderr)

    def _check_default_command(self):
        """检查是否有default命令"""
        for node in self.ast:
            if node["type"] == "default":
                self.has_default_command = True
                self.default_command = node
                break

    def _find_root_options(self):
        """查找根选项定义"""
        for node in self.ast:
            if node["type"] == "root_options":
                self.root_options = node["options"]
                # 构建根选项动作映射
                for option in self.root_options:
                    if "action" in option:
                        # 使用第一个标志作为动作的key
                        if option["flags"]:
                            flag = option["flags"][0].lstrip('-')
                            self.root_actions[flag] = option["action"]
                break

    def _build_parser(self):
        """构建argparse解析器"""
        if self.has_default_command:
            # 对于default命令，使用appname作为描述
            description = self.appname
            self.parser = argparse.ArgumentParser(description=description)

            # 添加根选项
            for option in self.root_options:
                self._add_option(self.parser, option)

            # 添加default命令的选项和参数
            body = self.default_command["body"]
            for option in body["options"]:
                self._add_option(self.parser, option)

            for argument in body["arguments"]:
                self._add_argument(self.parser, argument)

            # 设置默认处理函数
            action = body.get("action")
            if action:
                self.parser.set_defaults(
                    func=self._create_command_handler(action, self.default_command)
                )
        else:
            # 对于多命令程序，使用appname作为主描述
            self.parser = argparse.ArgumentParser(description=self.appname)

            # 添加根选项
            for option in self.root_options:
                self._add_option(self.parser, option)

            # 只有在有命令时才添加子命令
            commands = [node for node in self.ast if node["type"] == "command"]
            if commands:
                self.subparsers = self.parser.add_subparsers(dest='command', help='Available commands')

                # 为每个命令创建子解析器
                for node in commands:
                    self._add_command(node)

    def _add_command(self, command_node: Dict[str, Any]):
        """添加命令到解析器"""
        name = command_node["name"]
        description = command_node.get("description", "")

        # 创建子命令解析器
        subparser = self.subparsers.add_parser(name, help=description)

        # 添加命令特定的选项
        for option in command_node["body"]["options"]:
            self._add_option(subparser, option)

        # 添加命令特定的参数
        for argument in command_node["body"]["arguments"]:
            self._add_argument(subparser, argument)

        # 设置命令处理函数
        action = command_node["body"].get("action")
        if action:
            subparser.set_defaults(
                func=self._create_command_handler(action, command_node)
            )

    def _add_option(self, parser, option: Dict[str, Any]):
        """添加选项到解析器"""
        flags = option["flags"]
        data_type = option.get("data_type", "string")
        param_name = option.get("param")
        attributes = option.get("attributes", {})
        description = option.get("description", "")

        # 构建add_argument参数
        kwargs = {}

        # 设置类型
        if data_type == "bool":
            # 布尔选项通常作为标志处理
            # 使用 store_true 或 store_false 取决于默认值
            default_value = attributes.get("default", "false").lower() == "true"
            if default_value:
                kwargs["action"] = "store_false"
            else:
                kwargs["action"] = "store_true"
        elif data_type == "int":
            kwargs["type"] = int
        elif data_type == "float":
            kwargs["type"] = float
        # 字符串是默认类型，不需要特别设置

        # 设置默认值
        if "default" in attributes:
            default_value = attributes["default"]
            if data_type == "bool":
                default_value = default_value.lower() == "true"
                kwargs["default"] = default_value
            elif data_type == "int":
                kwargs["default"] = int(default_value)
            elif data_type == "float":
                kwargs["default"] = float(default_value)
            else:
                kwargs["default"] = default_value

        # 设置帮助文本
        if description:
            kwargs["help"] = description

        # 对于根选项，我们需要记录dest名以便后续处理
        dest_name = None
        if param_name and data_type != "bool":
            # 使用长标志名（去掉--前缀）作为dest
            for flag in flags:
                if flag.startswith("--"):
                    dest_name = flag[2:].replace('-', '_')
                    kwargs["dest"] = dest_name
                    break
                elif flag.startswith("-"):
                    # 如果没有长标志，使用短标志（去掉-前缀）
                    dest_name = flag[1:].replace('-', '_')
                    kwargs["dest"] = dest_name
            else:
                # 如果没有找到合适的标志，使用param_name
                dest_name = param_name
                kwargs["dest"] = dest_name
        else:
            # 没有参数的选项（标志）
            # 设置dest为标志名
            for flag in flags:
                if flag.startswith("--"):
                    dest_name = flag[2:].replace('-', '_')
                    kwargs["dest"] = dest_name
                    break
                elif flag.startswith("-"):
                    dest_name = flag[1:].replace('-', '_')
                    kwargs["dest"] = dest_name
            else:
                # 如果没有找到合适的标志，生成一个dest名
                if flags:
                    first_flag = flags[0].lstrip('-')
                    dest_name = first_flag.replace('-', '_')
                    kwargs["dest"] = dest_name

        # 存储dest名到option中，用于后续处理
        option["_dest_name"] = dest_name

        parser.add_argument(*flags, **kwargs)

    def _add_argument(self, parser, argument: Dict[str, Any]):
        """添加位置参数到解析器"""
        name = argument["name"]
        data_type = argument.get("data_type", "string")
        attributes = argument.get("attributes", {})
        description = argument.get("description", "")
        is_variadic = argument.get("variadic", False)

        # 构建add_argument参数
        kwargs = {}

        # 设置类型
        kwargs["type"] = self._get_python_type(data_type)

        # 设置默认值
        if "default" in attributes:
            default_value = attributes["default"]
            kwargs["default"] = self._convert_value(default_value, data_type)

        # 设置帮助文本
        if description:
            kwargs["help"] = description

        # 处理无限参数
        if is_variadic:
            # 无限参数使用 nargs='*' (0个或多个) 或 nargs='+' (1个或多个)
            # 根据是否有默认值来决定
            if "default" in attributes:
                kwargs["nargs"] = '*'  # 可选参数
            else:
                kwargs["nargs"] = '+'  # 必需参数
        else:
            # 普通参数
            # 修复：对于有默认值的参数，设置 nargs='?' 使其变为可选
            if "default" in attributes:
                kwargs["nargs"] = '?'
            elif attributes.get("required"):
                # 必需的参数，不设置nargs，argparse默认就是必需的
                pass
            else:
                # 没有默认值也不是必需的参数，设置为可选
                kwargs["nargs"] = '?'

        # 添加参数
        parser.add_argument(name, **kwargs)

    def _get_python_type(self, data_type: str) -> type:
        """将CLI数据类型转换为Python类型"""
        type_map = {
            "string": str,
            "int": int,
            "float": float,
            "bool": bool
        }
        return type_map.get(data_type, str)

    def _convert_value(self, value: str, data_type: str) -> Any:
        """根据数据类型转换值"""
        if data_type == "bool":
            return value.lower() == "true"
        elif data_type == "int":
            return int(value)
        elif data_type == "float":
            return float(value)
        else:
            return value

    def _create_command_handler(self, action: Dict[str, Any], command_node: Dict[str, Any]) -> Callable:
        """创建命令处理函数"""

        def command_handler(args):
            # 获取函数
            function_path = action["function"]
            func = self._get_function(function_path)
            if not func:
                print(f"Error: Function {function_path} not found", file=sys.stderr)
                return

            # 准备参数
            func_args = self._prepare_function_args(args, action.get("params", []), command_node)

            # 调用函数
            try:
                result = func(**func_args)
                if result is not None:
                    print(result)
            except Exception as e:
                print(f"Error executing command: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()

        return command_handler

    def _get_function(self, function_path: str) -> Callable | None:
        """获取函数对象"""
        # 如果没有导入任何模块，直接返回None
        if not self.imported_modules:
            return None

        # 使用第一个导入的模块作为基础
        base_module = next(iter(self.imported_modules.values()))

        # 按点分割函数路径
        parts = function_path.split('.')

        # 从基础模块开始，沿着路径查找
        current_obj = base_module
        for part in parts:
            if hasattr(current_obj, part):
                current_obj = getattr(current_obj, part)
            else:
                # 如果路径中的任何部分不存在，返回None
                return None

        # 确保最终找到的对象是可调用的
        if callable(current_obj):
            return current_obj

        return None

    def _prepare_function_args(self, args, param_names: List[str], command_node: Dict[str, Any]) -> Dict[str, Any]:
        """准备函数参数"""
        func_args = {}

        for param in param_names:
            # 去掉$前缀
            if param.startswith('$'):
                var_name = param[1:]
            else:
                var_name = param

            # 获取参数值
            value = getattr(args, var_name, None)

            # 如果直接获取失败，尝试从选项参数中查找
            if value is None:
                # 查找是否有选项使用这个变量名作为dest
                for option in command_node["body"]["options"]:
                    # 获取选项的dest名
                    dest_name = None
                    param_name = option.get("param")
                    flags = option.get("flags", [])

                    if param_name and option.get("data_type") != "bool":
                        # 对于有参数的选项，使用我们设置的dest名
                        for flag in flags:
                            if flag.startswith("--"):
                                dest_name = flag[2:].replace('-', '_')
                                break
                            elif flag.startswith("-"):
                                dest_name = flag[1:].replace('-', '_')
                        if not dest_name:
                            dest_name = param_name
                    else:
                        # 对于布尔标志，使用标志名作为dest
                        for flag in flags:
                            if flag.startswith("--"):
                                dest_name = flag[2:].replace('-', '_')
                                break
                            elif flag.startswith("-"):
                                dest_name = flag[1:].replace('-', '_')

                    if dest_name == var_name:
                        value = getattr(args, dest_name, None)
                        break

            # 检查是否是无限参数
            is_variadic = False
            for arg in command_node["body"]["arguments"]:
                if arg["name"] == var_name and arg.get("variadic", False):
                    is_variadic = True
                    break

            # 如果是无限参数，确保它是一个列表
            if is_variadic and value is not None and not isinstance(value, list):
                value = [value]

            func_args[var_name] = value

        return func_args

    def _execute_command(self):
        """执行命令"""
        args = self.parser.parse_args()

        # 首先检查是否有根选项被设置并且有对应的动作
        for option in self.root_options:
            dest_name = option.get("_dest_name")
            if dest_name and hasattr(args, dest_name):
                value = getattr(args, dest_name)

                # 对于布尔类型的选项，只要值为 True 就执行
                # 对于其他类型的选项，只有当值不为 None 且不为默认值时执行
                should_execute = False
                data_type = option.get("data_type", "string")

                if data_type == "bool":
                    # 对于布尔选项，如果设置了就执行
                    if value is True:
                        should_execute = True
                else:
                    # 非布尔类型，检查是否有设置值
                    default_value = option.get("attributes", {}).get("default")
                    # 对于有默认值的选项，只有当用户实际提供了值时才执行
                    if value is not None and (default_value is None or value != default_value):
                        should_execute = True

                if should_execute and "action" in option:
                    # 执行根选项对应的动作
                    action = option["action"]
                    func = self._get_function(action["function"])
                    if func:
                        # 准备参数
                        func_args = self._prepare_root_option_args(args, action.get("params", []), option)
                        try:
                            result = func(**func_args)
                            if result is not None:
                                print(result)
                            # 根选项执行后退出程序
                            sys.exit(0)
                        except Exception as e:
                            print(f"Error executing root option: {e}", file=sys.stderr)
                            import traceback
                            traceback.print_exc()
                            sys.exit(1)
                    else:
                        print(f"Error: Function {action['function']} not found", file=sys.stderr)
                        sys.exit(1)

        # 如果没有根选项被执行，检查是否有命令需要执行
        if hasattr(args, 'func'):
            args.func(args)
        else:
            # 如果没有找到处理函数，打印帮助信息
            if self.has_default_command:
                # 对于default命令，如果没有提供必需参数，argparse会自动显示错误
                pass
            else:
                # 对于多命令程序，如果没有指定命令，显示帮助
                self.parser.print_help()

    def _prepare_root_option_args(self, args, param_names: List[str], option: Dict[str, Any]) -> Dict[str, Any]:
        """准备根选项函数参数"""
        func_args = {}

        for param in param_names:
            # 去掉$前缀
            if param.startswith('$'):
                var_name = param[1:]
            else:
                var_name = param

            # 获取参数值
            value = getattr(args, var_name, None)

            # 如果直接获取失败，尝试从选项本身查找
            if value is None and var_name == option.get("_dest_name"):
                value = getattr(args, var_name, None)

            func_args[var_name] = value

        return func_args


def main():
    pass
