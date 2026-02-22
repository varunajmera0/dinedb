from enum import Enum, auto
from dataclasses import dataclass
from typing import Any

class TokenType(Enum):
    """
    An enumeration of token types for a hypothetical language or system.
    """
    IDENT = auto()
    NUMBER = auto()
    STRING = auto()
    COMMA = auto()
    LPAREN = auto()
    RPAREN = auto()
    STAR = auto()
    EQUAL = auto()
    SEMICOLON = auto()
    KEYWORD = auto()

@dataclass(frozen=True)
class Token:
    """Definition: one lexical token from SQL input.

    Example:
        Token(type=TokenType.KEYWORD, value="SELECT", pos=0)
    """

    type: TokenType
    value: str
    pos: int

@dataclass(frozen=True)
class CreateTable:
    """Definition: AST node for CREATE TABLE.

    Example:
        CreateTable(table_name="users", columns=[("id","INT",True),("name","TEXT",False)])
    """

    table_name: str
    columns: list[tuple[str, str, bool]]


@dataclass(frozen=True)
class Insert:
    """Definition: AST node for INSERT.

    Example:
        Insert(table_name="users", values=[1, "Asha"])
    """

    table_name: str
    values: list[Any]


@dataclass(frozen=True)
class Select:
    """Definition: AST node for SELECT.

    Example:
        Select(table_name="users", columns=["*"], where_column="id", where_value=1, limit=5)
    """

    table_name: str
    columns: list[str]
    where_column: str | None = None
    where_value: Any | None = None
    limit: int | None = None

def tokenize(sql: str) -> list[Token]:
    """Definition: convert SQL string to a list of tokens.

    Example:
        tokenize("SELECT * FROM users;")
    """
    tokens: list[Token] = []
    i = 0
    length = len(sql)

    keywords = {
        "CREATE",
        "TABLE",
        "INSERT",
        "INTO",
        "VALUES",
        "SELECT",
        "FROM",
        "WHERE",
        "LIMIT",
        "PRIMARY",
        "KEY",
    }

    while i < length:
        ch = sql[i]

        if ch.isspace():
            i += 1
            continue

        if ch == ",":
            tokens.append(Token(TokenType.COMMA, ch, i))
            i += 1
            continue
        if ch == "(":
            tokens.append(Token(TokenType.LPAREN, ch, i))
            i += 1
            continue
        if ch == ")":
            tokens.append(Token(TokenType.RPAREN, ch, i))
            i += 1
            continue
        if ch == "*":
            tokens.append(Token(TokenType.STAR, ch, i))
            i += 1
            continue
        if ch == "=":
            tokens.append(Token(TokenType.EQUAL, ch, i))
            i += 1
            continue
        if ch == ";":
            tokens.append(Token(TokenType.SEMICOLON, ch, i))
            i += 1
            continue

        if ch == "'":
            start = i
            i += 1
            value_chars: list[str] = []
            while i < length and sql[i] != "'":
                value_chars.append(sql[i])
                i += 1
            if i >= length:
                raise ValueError(f"Unterminated string starting at {start}")
            i += 1
            tokens.append(Token(TokenType.STRING, "".join(value_chars), start))
            continue

        if ch.isdigit():
            start = i
            while i < length and sql[i].isdigit():
                i += 1
            tokens.append(Token(TokenType.NUMBER, sql[start:i], start))
            continue

        if ch.isalpha() or ch == "_":
            start = i
            while i < length and (sql[i].isalnum() or sql[i] == "_"):
                i += 1
            value = sql[start:i]
            upper_value = value.upper()
            if upper_value in keywords:
                tokens.append(Token(TokenType.KEYWORD, upper_value, start))
            else:
                tokens.append(Token(TokenType.IDENT, value, start))
            continue

        raise ValueError(f"Unexpected character '{ch}' at position {i}")

    return tokens


def parse(sql: str) -> CreateTable | Insert | Select:
    """Definition: parse SQL into an AST node.

    Example:
        parse("INSERT INTO users VALUES (1, 'Asha');")
    """
    tokens = tokenize(sql)
    if not tokens:
        raise ValueError("Empty SQL")

    if _is_keyword(tokens, 0, "CREATE"):
        return _parse_create_table(tokens)
    if _is_keyword(tokens, 0, "INSERT"):
        return _parse_insert(tokens)
    if _is_keyword(tokens, 0, "SELECT"):
        return _parse_select(tokens)
    raise ValueError("Supported statements: CREATE TABLE, INSERT, SELECT")


def _parse_create_table(tokens: list[Token]) -> CreateTable:
    """Definition: parse CREATE TABLE tokens into CreateTable AST.

    Dry run example:
        Input SQL:
            CREATE TABLE users (id INT PRIMARY KEY, name TEXT);

        Token stream (simplified):
            [CREATE, TABLE, IDENT(users), LPAREN,
             IDENT(id), IDENT(INT), KEYWORD(PRIMARY), KEYWORD(KEY),
             COMMA, IDENT(name), IDENT(TEXT), RPAREN, SEMICOLON]

        Parse steps:
        1) Read CREATE TABLE
        2) Read table name: users
        3) Read column definitions:
           - id INT PRIMARY KEY
           - name TEXT
        4) Build CreateTable AST

        Result:
            CreateTable(
                table_name="users",
                columns=[("id","INT",True),("name","TEXT",False)]
            )
    """
    i = 0
    _expect_keyword(tokens, i, "CREATE")
    i += 1
    _expect_keyword(tokens, i, "TABLE")
    i += 1
    table_name = _expect_ident(tokens, i).value
    i += 1
    _expect(tokens, i, TokenType.LPAREN)
    i += 1

    columns: list[tuple[str, str, bool]] = []
    while True:
        name_token = _expect_ident(tokens, i)
        i += 1
        type_token = _expect_ident(tokens, i)
        i += 1
        is_pk = False
        if _is_keyword(tokens, i, "PRIMARY"):
            _expect_keyword(tokens, i, "PRIMARY")
            i += 1
            _expect_keyword(tokens, i, "KEY")
            i += 1
            is_pk = True
        columns.append((name_token.value, type_token.value.upper(), is_pk))

        if _match(tokens, i, TokenType.COMMA):
            i += 1
            continue
        _expect(tokens, i, TokenType.RPAREN)
        i += 1
        break

    _consume_optional_semicolon(tokens, i)
    return CreateTable(table_name=table_name, columns=columns)


def _parse_insert(tokens: list[Token]) -> Insert:
    """Definition: parse INSERT tokens into Insert AST.

    Dry run example:
        Input SQL:
            INSERT INTO users VALUES (1, 'Asha');

        Token stream (simplified):
            [INSERT, INTO, IDENT(users), VALUES, LPAREN,
             NUMBER(1), COMMA, STRING(Asha), RPAREN, SEMICOLON]

        Parse steps:
        1) Read INSERT INTO
        2) Read table name: users
        3) Read VALUES list: [1, "Asha"]
        4) Build Insert AST

        Result:
            Insert(table_name="users", values=[1, "Asha"])
    """
    i = 0
    _expect_keyword(tokens, i, "INSERT")
    i += 1
    _expect_keyword(tokens, i, "INTO")
    i += 1
    table_name = _expect_ident(tokens, i).value
    i += 1
    _expect_keyword(tokens, i, "VALUES")
    i += 1
    _expect(tokens, i, TokenType.LPAREN)
    i += 1

    values: list[Any] = []
    while True:
        token = tokens[i]
        if token.type == TokenType.NUMBER:
            values.append(int(token.value))
        elif token.type == TokenType.STRING:
            values.append(token.value)
        else:
            raise ValueError(f"Unexpected token {token.type} at {token.pos}")
        i += 1

        if _match(tokens, i, TokenType.COMMA):
            i += 1
            continue
        _expect(tokens, i, TokenType.RPAREN)
        i += 1
        break

    _consume_optional_semicolon(tokens, i)
    return Insert(table_name=table_name, values=values)


def _parse_select(tokens: list[Token]) -> Select:
    """Definition: parse SELECT tokens into Select AST.

    Dry run example:
        Input SQL:
            SELECT * FROM users WHERE id = 1 LIMIT 5;

        Token stream (simplified):
            [SELECT, STAR, FROM, IDENT(users), WHERE, IDENT(id), EQUAL, NUMBER(1), LIMIT, NUMBER(5), SEMICOLON]

        Parse steps:
        1) Read SELECT
        2) Read columns: STAR -> ["*"]
        3) Read FROM + table: users
        4) Read WHERE: id = 1
        5) Read LIMIT: 5

        Result:
            Select(
                table_name="users",
                columns=["*"],
                where_column="id",
                where_value=1,
                limit=5,
            )
    """
    i = 0
    _expect_keyword(tokens, i, "SELECT")
    i += 1

    columns: list[str] = []
    if _match(tokens, i, TokenType.STAR):
        columns.append("*")
        i += 1
    else:
        while True:
            col_token = _expect_ident(tokens, i)
            columns.append(col_token.value)
            i += 1
            if _match(tokens, i, TokenType.COMMA):
                i += 1
                continue
            break

    _expect_keyword(tokens, i, "FROM")
    i += 1
    table_name = _expect_ident(tokens, i).value
    i += 1

    where_column = None
    where_value = None
    if _is_keyword(tokens, i, "WHERE"):
        i += 1
        where_column = _expect_ident(tokens, i).value
        i += 1
        _expect(tokens, i, TokenType.EQUAL)
        i += 1
        token = tokens[i]
        if token.type == TokenType.NUMBER:
            where_value = int(token.value)
        elif token.type == TokenType.STRING:
            where_value = token.value
        else:
            raise ValueError(f"Unexpected token {token.type} at {token.pos}")
        i += 1

    limit = None
    if _is_keyword(tokens, i, "LIMIT"):
        i += 1
        token = _expect(tokens, i, TokenType.NUMBER)
        limit = int(token.value)
        i += 1

    _consume_optional_semicolon(tokens, i)
    return Select(
        table_name=table_name,
        columns=columns,
        where_column=where_column,
        where_value=where_value,
        limit=limit,
    )


def _consume_optional_semicolon(tokens: list[Token], i: int) -> None:
    """Definition: consume trailing semicolon if present and assert end.

    Dry run example:
        Input tokens end with SEMICOLON -> consume it.
        If extra tokens remain -> raise error.
    """
    if i < len(tokens) and tokens[i].type == TokenType.SEMICOLON:
        i += 1
    if i != len(tokens):
        raise ValueError(f"Unexpected token {tokens[i].type} at {tokens[i].pos}")


def _expect(tokens: list[Token], i: int, token_type: TokenType) -> Token:
    """Definition: assert a token type at position i.

    Dry run example:
        Expect LPAREN at i=3, fail if not present.
    """
    if i >= len(tokens):
        raise ValueError(f"Expected {token_type} at end of input")
    token = tokens[i]
    if token.type != token_type:
        raise ValueError(f"Expected {token_type} at {token.pos}")
    return token


def _expect_ident(tokens: list[Token], i: int) -> Token:
    """Definition: assert identifier token at position i.

    Dry run example:
        Expect IDENT(users) after FROM.
    """
    if i >= len(tokens):
        raise ValueError("Expected identifier at end of input")
    token = tokens[i]
    if token.type != TokenType.IDENT:
        raise ValueError(f"Expected IDENT at {token.pos}")
    return token


def _expect_keyword(tokens: list[Token], i: int, value: str) -> None:
    """Definition: assert keyword token at position i.

    Dry run example:
        Expect KEYWORD(SELECT) at the start of a SELECT statement.
    """
    if i >= len(tokens):
        raise ValueError(f"Expected {value} at end of input")
    token = tokens[i]
    if token.type != TokenType.KEYWORD or token.value.upper() != value:
        raise ValueError(f"Expected {value} at {token.pos}")


def _is_keyword(tokens: list[Token], i: int, value: str) -> bool:
    """Definition: check if token at position i is a keyword.

    Dry run example:
        Check if tokens[i] == KEYWORD("WHERE").
    """
    if i >= len(tokens):
        return False
    token = tokens[i]
    return token.type == TokenType.KEYWORD and token.value.upper() == value


def _match(tokens: list[Token], i: int, token_type: TokenType) -> bool:
    """Definition: check if token at position i matches token_type.

    Dry run example:
        Check if tokens[i] == COMMA before continuing column list.
    """
    return i < len(tokens) and tokens[i].type == token_type
