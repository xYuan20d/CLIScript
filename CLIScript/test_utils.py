import sys
import subprocess
import os
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from typing import List, Dict, Any, Optional, Tuple
import tempfile


class CLITestRunner:
    """CLI测试运行器 - 用于测试CLI命令的输出和错误"""

    def __init__(self, main_module_path: str):
        """
        初始化测试运行器

        Args:
            main_module_path: 主模块的路径，例如 "main.py"
        """
        self.main_module_path = main_module_path
        self.temp_files = []

    def run_command(self, args: List[str], input_text: str = None,
                    capture_output: bool = True) -> Dict[str, Any]:
        """
        运行命令并返回结果

        Args:
            args: 命令行参数列表，例如 ["-v", "file-copy", "source.txt", "target.txt"]
            input_text: 标准输入内容
            capture_output: 是否捕获输出

        Returns:
            包含执行结果的字典
        """
        cmd = [sys.executable, self.main_module_path] + args

        try:
            if capture_output:
                result = subprocess.run(
                    cmd,
                    input=input_text,
                    text=True,
                    capture_output=True,
                    timeout=30  # 30秒超时
                )

                return {
                    "success": result.returncode == 0,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "command": " ".join(cmd)
                }
            else:
                # 不捕获输出，直接显示
                result = subprocess.run(cmd, input=input_text, text=True)
                return {
                    "success": result.returncode == 0,
                    "exit_code": result.returncode,
                    "stdout": "",
                    "stderr": "",
                    "command": " ".join(cmd)
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": "Command timed out after 30 seconds",
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Error running command: {e}",
                "command": " ".join(cmd)
            }

    def assert_success(self, args: List[str], input_text: str = None,
                       message: str = None) -> Dict[str, Any]:
        """
        运行命令并断言成功

        Args:
            args: 命令行参数列表
            input_text: 标准输入内容
            message: 断言失败时的消息

        Returns:
            执行结果

        Raises:
            AssertionError: 如果命令执行失败
        """
        result = self.run_command(args, input_text)

        if not result["success"]:
            msg = message or f"Command failed: {result['command']}\nSTDERR: {result['stderr']}"
            raise AssertionError(msg)

        return result

    def assert_failure(self, args: List[str], input_text: str = None,
                       message: str = None) -> Dict[str, Any]:
        """
        运行命令并断言失败

        Args:
            args: 命令行参数列表
            input_text: 标准输入内容
            message: 断言失败时的消息

        Returns:
            执行结果

        Raises:
            AssertionError: 如果命令执行成功
        """
        result = self.run_command(args, input_text)

        if result["success"]:
            msg = message or f"Command succeeded unexpectedly: {result['command']}"
            raise AssertionError(msg)

        return result

    def assert_output_contains(self, args: List[str], expected_text: str,
                               input_text: str = None, message: str = None) -> Dict[str, Any]:
        """
        运行命令并断言输出包含特定文本

        Args:
            args: 命令行参数列表
            expected_text: 期望的输出文本
            input_text: 标准输入内容
            message: 断言失败时的消息

        Returns:
            执行结果

        Raises:
            AssertionError: 如果输出不包含期望的文本
        """
        result = self.assert_success(args, input_text)

        if expected_text not in result["stdout"] and expected_text not in result["stderr"]:
            msg = message or (f"Output does not contain expected text: '{expected_text}'\n"
                              f"STDOUT: {result['stdout']}\nSTDERR: {result['stderr']}")
            raise AssertionError(msg)

        return result

    def assert_output_not_contains(self, args: List[str], unexpected_text: str,
                                   input_text: str = None, message: str = None) -> Dict[str, Any]:
        """
        运行命令并断言输出不包含特定文本

        Args:
            args: 命令行参数列表
            unexpected_text: 不期望的输出文本
            input_text: 标准输入内容
            message: 断言失败时的消息

        Returns:
            执行结果

        Raises:
            AssertionError: 如果输出包含不期望的文本
        """
        result = self.assert_success(args, input_text)

        if unexpected_text in result["stdout"] or unexpected_text in result["stderr"]:
            msg = message or (f"Output contains unexpected text: '{unexpected_text}'\n"
                              f"STDOUT: {result['stdout']}\nSTDERR: {result['stderr']}")
            raise AssertionError(msg)

        return result

    def create_temp_file(self, content: str = "", suffix: str = ".txt") -> str:
        """
        创建临时文件

        Args:
            content: 文件内容
            suffix: 文件后缀

        Returns:
            临时文件路径
        """
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        self.temp_files.append(path)
        return path

    def cleanup(self):
        """清理临时文件"""
        for path in self.temp_files:
            try:
                os.unlink(path)
            except:
                pass  # 忽略删除错误
        self.temp_files = []


class InMemoryCLITester:
    """
    内存中的CLI测试器 - 不通过子进程，直接在内存中测试

    注意：这个测试器需要能够访问CLI解析器和运行器的代码
    """

    def __init__(self, cli_parser_class, cli_runner_class):
        """
        初始化内存测试器

        Args:
            cli_parser_class: CLI解析器类
            cli_runner_class: CLI运行器类
        """
        self.cli_parser_class = cli_parser_class
        self.cli_runner_class = cli_runner_class
        self.source_code = None

    def set_source(self, source_code: str):
        """设置CLI源代码"""
        self.source_code = source_code

    def run_test(self, args: List[str], source_code: str = None) -> Dict[str, Any]:
        """
        在内存中运行测试

        Args:
            args: 命令行参数列表
            source_code: CLI源代码，如果为None则使用之前设置的代码

        Returns:
            测试结果
        """
        if source_code is None:
            source_code = self.source_code

        if source_code is None:
            raise ValueError("No source code provided")

        # 备份sys.argv
        old_argv = sys.argv

        try:
            # 设置新的sys.argv
            sys.argv = ["test_runner"] + args

            # 重定向stdout和stderr
            stdout_capture = StringIO()
            stderr_capture = StringIO()

            exit_code = 0

            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                try:
                    # 解析CLI源代码
                    parser = self.cli_parser_class()
                    result = parser.parse(source_code)

                    # 运行CLI
                    runner = self.cli_runner_class(result["ast"])
                    runner.run()

                except SystemExit as e:
                    exit_code = e.code
                except Exception as e:
                    stderr_capture.write(f"Error: {e}")
                    exit_code = 1

            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue(),
                "command": " ".join(["python", "test_runner"] + args)
            }

        finally:
            # 恢复sys.argv
            sys.argv = old_argv


# 测试用例示例
def run_comprehensive_tests(test_runner: CLITestRunner):
    """
    运行全面的CLI测试

    Args:
        test_runner: 测试运行器实例
    """
    print("=== 开始全面CLI测试 ===")

    try:
        # 测试1: 根选项 -v
        print("测试1: 根选项 -v")
        result = test_runner.assert_success(["-v"])
        print("✓ 根选项 -v 测试通过")

        # 测试2: 根选项 --version
        print("测试2: 根选项 --version")
        result = test_runner.assert_success(["--version"])
        print("✓ 根选项 --version 测试通过")

        # 测试3: 根选项 -u 使用默认值
        print("测试3: 根选项 -u 使用默认值")
        result = test_runner.assert_success(["-u"])
        print("✓ 根选项 -u 使用默认值测试通过")

        # 测试4: 根选项 --update 使用指定值
        print("测试4: 根选项 --update 使用指定值")
        result = test_runner.assert_success(["--update", "2.0.0"])
        print("✓ 根选项 --update 使用指定值测试通过")

        # 测试5: 命令 file-copy
        print("测试5: 命令 file-copy")
        # 创建临时文件用于测试
        source_file = test_runner.create_temp_file("test content")
        target_file = test_runner.create_temp_file(suffix="_target.txt")

        result = test_runner.assert_success([
            "file-copy",
            "-r", "-f",
            source_file,
            target_file
        ])
        print("✓ 命令 file-copy 测试通过")

        # 测试6: 命令 search
        print("测试6: 命令 search")
        result = test_runner.assert_success([
            "search",
            "-p", "*.txt",
            "-c",
            "/tmp"
        ])
        print("✓ 命令 search 测试通过")

        # 测试7: 命令 info
        print("测试7: 命令 info")
        result = test_runner.assert_success(["info"])
        print("✓ 命令 info 测试通过")

        # 测试8: 命令 sudo
        print("测试8: 命令 sudo")
        result = test_runner.assert_success([
            "sudo",
            "-u", "admin",
            "ls", "-la"
        ])
        print("✓ 命令 sudo 测试通过")

        # 测试9: 帮助信息
        print("测试9: 帮助信息")
        result = test_runner.assert_success(["--help"])
        print("✓ 帮助信息测试通过")

        # 测试10: 子命令帮助
        print("测试10: 子命令帮助")
        result = test_runner.assert_success(["file-copy", "--help"])
        print("✓ 子命令帮助测试通过")

        print("=== 所有测试通过! ===")

    except AssertionError as e:
        print(f"❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        return False
    finally:
        # 清理临时文件
        test_runner.cleanup()

    return True


def run_regression_tests(test_runner: CLITestRunner):
    """
    运行回归测试 - 确保之前修复的问题没有再次出现

    Args:
        test_runner: 测试运行器实例
    """
    print("=== 开始回归测试 ===")

    try:
        # 回归测试1: 布尔根选项 -v 应该工作
        print("回归测试1: 布尔根选项 -v")
        result = test_runner.assert_success(["-v"])
        assert result["exit_code"] == 0, "布尔根选项 -v 应该成功退出"
        print("✓ 布尔根选项 -v 回归测试通过")

        # 回归测试2: 有默认值的根选项 -u 应该工作（不提供参数值）
        print("回归测试2: 有默认值的根选项 -u")
        result = test_runner.assert_success(["-u"])
        assert result["exit_code"] == 0, "有默认值的根选项 -u 应该成功退出"
        print("✓ 有默认值的根选项 -u 回归测试通过")

        # 回归测试3: 根选项和命令同时使用时，根选项应该优先执行
        print("回归测试3: 根选项优先执行")
        result = test_runner.assert_success(["-v", "file-copy", "source.txt", "target.txt"])
        # 这里应该执行根选项并退出，不会执行file-copy命令
        assert result["exit_code"] == 0, "根选项应该优先执行"
        print("✓ 根选项优先执行回归测试通过")

        print("=== 所有回归测试通过! ===")

    except AssertionError as e:
        print(f"❌ 回归测试失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 回归测试出错: {e}")
        return False

    return True


if __name__ == "__main__":
    # 使用示例
    test_runner = CLITestRunner("")

    # 运行全面测试
    success = run_comprehensive_tests(test_runner)

    if success:
        # 运行回归测试
        run_regression_tests(test_runner)
    else:
        print("全面测试失败，跳过回归测试")
