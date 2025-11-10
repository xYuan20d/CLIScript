from dataclasses import dataclass
from typing import List, Optional, Any, Dict
from enum import Enum
import re
import json


# ==================== Token定义 ====================

class TokenType(Enum):
    APPNAME = "appname"
    USE = "use"
    CMD = "cmd"
    DEFAULT = "default"
    OPTION = "option"
    ARGUMENT = "argument"
    ARROW = "arrow"
    STRING = "string"
    IDENTIFIER = "identifier"
    FLAG = "flag"
    TYPE = "type"
    ATTRIBUTE = "attribute"
    COMMA = "comma"
    NEWLINE = "newline"
    LPAREN = "lparen"
    RPAREN = "rparen"
    ROOT = "root"
    DOLLAR = "dollar"
    EOF = "eof"


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int
    metadata: Optional[Dict[str, Any]] = None

    def __repr__(self):
        return f"Token({self.type.name}, '{self.value}', line:{self.line}, col:{self.column})"


# ==================== 词法分析器 ====================

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

        # 词法规则定义
        self.rules = [
            # 关键字
            (TokenType.USE, r'use\b'),
            (TokenType.CMD, r'cmd\b'),
            (TokenType.DEFAULT, r'default\b'),
            (TokenType.OPTION, r'option\b'),
            (TokenType.ROOT, r'root\b'),
            (TokenType.APPNAME, r'appname\b'),
            (TokenType.ARROW, r'->'),

            # 标点符号
            (TokenType.COMMA, r','),
            (TokenType.LPAREN, r'\('),
            (TokenType.RPAREN, r'\)'),
            (TokenType.DOLLAR, r'\$'),

            # 标识符和特殊格式
            (TokenType.FLAG, r'--?[a-zA-Z0-9\-]+'),
            (TokenType.TYPE, r'\[(bool|string|int|float|choice:[^\]]+)\]'),
            (TokenType.ATTRIBUTE, r'\[(required|default:[^\]]+|multiple|if\([^)]+\))\]'),
            # 使用更复杂的正则表达式匹配带转义字符的字符串
            (TokenType.STRING, r'"([^"\\]|\\.)*"'),
            (TokenType.IDENTIFIER, r'<[^>]+>'),
            (TokenType.IDENTIFIER, r'[a-zA-Z_][a-zA-Z0-9_\-\.]*'),

            # 空白和注释（跳过）
            (None, r'[ \t]+'),
            (None, r'#.*'),

            # 换行符
            (TokenType.NEWLINE, r'\n'),
        ]

    def tokenize(self) -> List[Token]:
        """将源代码转换为token列表"""
        while self.position < len(self.source):
            self._read_next_token()

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens

    def _read_next_token(self):
        """读取下一个token"""
        remaining_text = self.source[self.position:]

        for pattern_type, pattern in self.rules:
            match = re.match(pattern, remaining_text)
            if match:
                value = match.group(0)
                start_line, start_col = self.line, self.column

                # 更新位置
                self._update_position(value)

                # 如果是跳过模式，不生成token
                if pattern_type is None:
                    return

                # 处理特殊token类型
                actual_token_type = pattern_type
                processed_value = value

                if pattern_type == TokenType.IDENTIFIER and value.startswith('<'):
                    actual_token_type = TokenType.ARGUMENT
                    processed_value = value[1:-1]
                elif pattern_type == TokenType.TYPE:
                    processed_value = value[1:-1]
                elif pattern_type == TokenType.ATTRIBUTE:
                    processed_value = value[1:-1]
                elif pattern_type == TokenType.STRING:
                    # 修复：处理字符串中的转义字符
                    # 先去掉引号，然后解码转义序列
                    processed_value = self._unescape_string(value[1:-1])

                # 创建token
                token = Token(actual_token_type, processed_value, start_line, start_col)
                self.tokens.append(token)
                return

        raise SyntaxError(f"Unexpected character at line {self.line}, column {self.column}: "
                          f"'{self.source[self.position]}'")

    def _unescape_string(self, s: str) -> str:
        """处理字符串中的转义序列"""
        try:
            # 使用 bytes 和 decode 处理转义序列
            return bytes(s, "utf-8").decode("unicode_escape")
        except UnicodeDecodeError:
            # 如果解码失败，返回原始字符串
            return s

    def _update_position(self, text: str):
        """更新行列位置"""
        for char in text:
            if char == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.position += 1


# ==================== 语法分析器 ====================

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.ast = []
        self.has_default = False
        self.has_commands = False
        self.root_options = []

    def parse(self) -> List[Dict]:
        """解析token流为AST"""
        while not self._is_eof():
            if self._match(TokenType.NEWLINE):
                self._advance()
                continue

            # 解析各种语句类型
            if self._match(TokenType.APPNAME):
                self.ast.append(self._parse_appname_statement())
            elif self._match(TokenType.USE):
                self.ast.append(self._parse_use_statement())
            elif self._match(TokenType.ROOT):  # 解析根选项
                self.root_options.append(self._parse_root_option())
            elif self._match(TokenType.CMD):
                if self.has_default:
                    raise SyntaxError("Cannot use 'cmd' after 'default' command")
                self.has_commands = True
                self.ast.append(self._parse_command())
            elif self._match(TokenType.DEFAULT):
                if self.has_commands or self.has_default:
                    raise SyntaxError("Cannot use 'default' with other commands")
                self.has_default = True
                self.ast.append(self._parse_default_command())
            else:
                self._advance()

        # 将根选项添加到AST中
        if self.root_options:
            self.ast.append({
                "type": "root_options",
                "options": self.root_options
            })

        return self.ast

    def _parse_root_option(self) -> Dict:
        """解析根选项定义"""
        root_token = self._advance()

        # 解析选项定义
        option = self._parse_option()
        option["line"] = root_token.line

        # 检查是否有动作定义
        if self._match(TokenType.ARROW):
            action = self._parse_action()
            option["action"] = action

        return option

    def _parse_use_statement(self) -> Dict:
        """解析use语句"""
        use_token = self._advance()
        module_token = self._expect(TokenType.STRING)

        return {
            "type": "use",
            "module": module_token.value,
            "line": use_token.line
        }

    def _parse_appname_statement(self) -> Dict:
        """解析appname语句"""
        appname_token = self._advance()
        name_token = self._expect(TokenType.STRING)

        return {
            "type": "appname",
            "name": name_token.value,
            "line": appname_token.line
        }

    def _parse_command(self) -> Dict:
        """解析命令定义"""
        cmd_token = self._advance()
        name_token = self._expect(TokenType.IDENTIFIER)

        description = None
        if self._match(TokenType.STRING):
            description_token = self._advance()
            description = description_token.value

        body = self._parse_command_body()

        return {
            "type": "command",
            "name": name_token.value,
            "description": description,
            "body": body,
            "line": cmd_token.line
        }

    def _parse_default_command(self) -> Dict:
        """解析default命令定义"""
        default_token = self._advance()
        description_token = self._expect(TokenType.STRING)

        body = self._parse_command_body()

        return {
            "type": "default",
            "description": description_token.value,
            "body": body,
            "line": default_token.line
        }

    def _parse_command_body(self) -> Dict:
        """解析命令体"""
        options = []
        arguments = []
        action = None

        while not self._is_eof() and not self._match(TokenType.CMD) and not self._match(
                TokenType.DEFAULT) and not self._match(TokenType.USE):
            if self._match(TokenType.NEWLINE):
                self._advance()
                continue

            if self._match(TokenType.FLAG):
                options.append(self._parse_option())
            elif self._match(TokenType.ARGUMENT):
                arguments.append(self._parse_argument())
            elif self._match(TokenType.ARROW):
                action = self._parse_action()
            else:
                self._advance()

        return {
            "options": options,
            "arguments": arguments,
            "action": action
        }

    def _parse_option(self) -> Dict:
        """解析选项定义"""
        flags = []

        while self._match(TokenType.FLAG):
            flags.append(self._advance().value)
            if self._match(TokenType.COMMA):
                self._advance()

        option_param = None
        if self._match(TokenType.ARGUMENT):
            option_param_token = self._advance()
            option_param = option_param_token.value

        option_type = None
        attributes = {}
        description = None

        if self._match(TokenType.TYPE):
            type_token = self._advance()
            option_type = type_token.value

        while self._match(TokenType.ATTRIBUTE):
            attr_token = self._advance()
            attr_value = attr_token.value

            if ':' in attr_value:
                key, value = attr_value.split(':', 1)
                attributes[key] = value
            else:
                attributes[attr_value] = True

        if self._match(TokenType.STRING):
            desc_token = self._advance()
            description = desc_token.value

        if self._match(TokenType.NEWLINE):
            self._advance()

        return {
            "type": "option",
            "flags": flags,
            "param": option_param,
            "data_type": option_type,
            "attributes": attributes,
            "description": description
        }

    def _parse_argument(self) -> Dict:
        """解析参数定义"""
        name_token = self._advance()
        name = name_token.value

        is_variadic = False
        if name.endswith('...'):
            is_variadic = True
            name = name[:-3]

        arg_type = None
        attributes = {}
        description = None

        if self._match(TokenType.TYPE):
            type_token = self._advance()
            arg_type = type_token.value

        while self._match(TokenType.ATTRIBUTE):
            attr_token = self._advance()
            attr_value = attr_token.value

            if ':' in attr_value:
                key, value = attr_value.split(':', 1)
                attributes[key] = value
            else:
                attributes[attr_value] = True

        if self._match(TokenType.STRING):
            desc_token = self._advance()
            description = desc_token.value

        if self._match(TokenType.NEWLINE):
            self._advance()

        return {
            "type": "argument",
            "name": name,
            "data_type": arg_type,
            "attributes": attributes,
            "description": description,
            "variadic": is_variadic
        }

    def _parse_action(self) -> Dict:
        """解析动作定义"""
        arrow_token = self._advance()
        function_token = self._expect(TokenType.IDENTIFIER)

        params = []
        if self._match(TokenType.LPAREN):
            self._advance()

            while not self._match(TokenType.RPAREN) and not self._is_eof():
                if self._match(TokenType.DOLLAR):
                    self._advance()
                    param_token = self._expect(TokenType.IDENTIFIER)
                    params.append(f"${param_token.value}")

                    if self._match(TokenType.COMMA):
                        self._advance()
                else:
                    break

            if self._match(TokenType.RPAREN):
                self._advance()

        if self._match(TokenType.NEWLINE):
            self._advance()

        return {
            "type": "action",
            "function": function_token.value,
            "params": params,
            "line": arrow_token.line
        }

    def _match(self, token_type: TokenType) -> bool:
        if self._is_eof():
            return False
        return self.tokens[self.position].type == token_type

    def _expect(self, token_type: TokenType) -> Token:
        if self._match(token_type):
            return self._advance()
        current_token = self.tokens[self.position] if not self._is_eof() else self.tokens[-1]
        raise SyntaxError(
            f"Expected {token_type}, got {current_token.type} at line {current_token.line}, column {current_token.column}")

    def _advance(self) -> Token:
        if not self._is_eof():
            token = self.tokens[self.position]
            self.position += 1
            return token
        return self.tokens[-1]

    def _is_eof(self) -> bool:
        return self.position >= len(self.tokens) or self.tokens[self.position].type == TokenType.EOF


# ==================== CLIScript解析器主类 ====================

class CLIScriptParser:
    def __init__(self):
        self.lexer = None
        self.parser = None

    def parse(self, source: str) -> Dict[str, Any]:
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()

        self.parser = Parser(tokens)
        ast = self.parser.parse()

        return {
            "tokens": tokens,
            "ast": ast,
            "source": source
        }

    def print_tokens(self, tokens: List[Token] = None):
        if tokens is None and self.lexer:
            tokens = self.lexer.tokens

        print("=== Tokens ===")
        for token in tokens:
            print(token)

    def print_ast(self, ast: List[Dict] = None):
        if ast is None and self.parser:
            ast = self.parser.ast

        print("\n=== AST ===")
        print(json.dumps(ast, indent=2, ensure_ascii=False))
