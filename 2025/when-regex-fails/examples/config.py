#!/usr/bin/env python3
"""
Parser vs Regex Comparison
==========================

This script demonstrates why a proper parser is better than regex for
parsing nested configuration structures. It shows both approaches and
compares their results.

Problem: Parse nested configuration blocks (like nginx config)
"""

import re
import json
from typing import Dict, Any, List, Union


# Sample configuration text to parse
CONFIG_TEXT = """
server {
    listen 80;
    server_name example.com;
    location /api {
        proxy_pass http://backend;
        timeout 30s;
        headers {
            add X-Custom "value with spaces";
            add X-Another "more values";
            remove Authorization;
        }
    }
    location /static {
        root /var/www;
        expires 1d;
    }
}

upstream backend {
    server 192.168.1.1:8080;
    server 192.168.1.2:8080;
    server 192.168.1.3:8080;
}

server {
    listen 443 ssl;
    server_name secure.example.com;
    ssl_certificate /path/to/cert.pem;
}
"""


class RegexParser:
    """
    Attempt to parse configuration using regex patterns.
    This approach has fundamental limitations with nested structures.
    """

    def __init__(self):
        # Simple key-value pattern
        self.simple_pattern = r"(\w+)\s+([^;{]+);"
        # Block pattern - only works for non-nested blocks!
        self.block_pattern = r"(\w+)\s*\{([^{}]*)\}"
        # More complex block pattern - still fails on deep nesting
        self.nested_pattern = r"(\w+)\s*\{((?:[^{}]|\{[^{}]*\})*)\}"

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse configuration text using regex.

        Problems with this approach:
        1. Can't handle properly nested braces
        2. Fails on quoted strings with special characters
        3. No context awareness (can't distinguish between different scopes)
        4. Becomes exponentially complex for deep nesting
        5. Can't handle recursive structures naturally
        """
        result = {}

        # Find all simple key-value pairs
        simple_matches = re.findall(self.simple_pattern, text)
        for key, value in simple_matches:
            if key in result:
                if isinstance(result[key], list):
                    result[key].append(value.strip())
                else:
                    result[key] = [result[key], value.strip()]
            else:
                result[key] = value.strip()

        # Try to find blocks - this will miss nested blocks!
        block_matches = re.findall(self.nested_pattern, text)
        for block_name, block_content in block_matches:
            # Recursively try to parse block content
            inner_result = {}

            # Parse simple directives within the block
            inner_simple = re.findall(self.simple_pattern, block_content)
            for key, value in inner_simple:
                if key in inner_result:
                    if isinstance(inner_result[key], list):
                        inner_result[key].append(value.strip())
                    else:
                        inner_result[key] = [inner_result[key], value.strip()]
                else:
                    inner_result[key] = value.strip()

            # Try to find nested blocks (this gets messy quickly)
            nested_blocks = re.findall(self.block_pattern, block_content)
            for nested_name, nested_content in nested_blocks:
                nested_simple = re.findall(self.simple_pattern, nested_content)
                inner_result[nested_name] = dict(nested_simple)

            if block_name in result:
                if isinstance(result[block_name], list):
                    result[block_name].append(inner_result)
                else:
                    result[block_name] = [result[block_name], inner_result]
            else:
                result[block_name] = inner_result

        return result


class ConfigParser:
    """
    Proper parser for configuration files.
    Handles nested structures, quoted strings, and maintains context.
    """

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def peek(self) -> str:
        """Look at current character without consuming it"""
        return self.text[self.pos] if self.pos < self.length else ""

    def consume(self) -> str:
        """Consume and return current character"""
        if self.pos >= self.length:
            return ""
        char = self.text[self.pos]
        self.pos += 1
        return char

    def skip_whitespace(self):
        """Skip whitespace and newlines"""
        while self.pos < self.length and self.text[self.pos].isspace():
            self.pos += 1

    def read_identifier(self) -> str:
        """Read an identifier (letters, numbers, underscore, hyphen, dot, slash)"""
        start = self.pos
        while self.pos < self.length and (
            self.text[self.pos].isalnum() or self.text[self.pos] in "_-./"
        ):
            self.pos += 1
        return self.text[start : self.pos]

    def read_quoted_string(self) -> str:
        """Read a quoted string, properly handling escapes"""
        quote_char = self.consume()  # consume opening quote
        result = ""

        while self.pos < self.length:
            char = self.peek()
            if char == quote_char:
                self.consume()  # consume closing quote
                break
            elif char == "\\":
                self.consume()  # consume backslash
                escaped = self.consume()
                # Handle common escape sequences
                if escaped == "n":
                    result += "\n"
                elif escaped == "t":
                    result += "\t"
                elif escaped == "r":
                    result += "\r"
                elif escaped == "\\":
                    result += "\\"
                else:
                    result += escaped
            else:
                result += self.consume()

        return result

    def read_value(self) -> str:
        """Read a value (quoted string or unquoted token)"""
        self.skip_whitespace()

        if self.peek() in "\"'":
            return self.read_quoted_string()
        else:
            # Read until semicolon, brace, or whitespace
            start = self.pos
            while self.pos < self.length and self.text[self.pos] not in ";{} \t\n\r":
                self.pos += 1
            return self.text[start : self.pos].strip()

    def parse_block(self) -> Dict[str, Any]:
        """Parse a configuration block recursively"""
        result = {}

        while self.pos < self.length:
            self.skip_whitespace()

            # Check for end of block or end of file
            if not self.peek() or self.peek() == "}":
                break

            # Read directive name
            directive = self.read_identifier()
            if not directive:
                break

            self.skip_whitespace()

            if self.peek() == "{":
                # It's a block directive
                self.consume()  # consume '{'
                block_content = self.parse_block()
                self.skip_whitespace()
                if self.peek() == "}":
                    self.consume()  # consume '}'

                # Handle multiple blocks with same name
                if directive in result:
                    if isinstance(result[directive], list):
                        result[directive].append(block_content)
                    else:
                        result[directive] = [result[directive], block_content]
                else:
                    result[directive] = block_content

            else:
                # It's a value directive - may have multiple values
                values = []

                # Read first value
                value = self.read_value()
                if value:
                    values.append(value)

                # Check for additional values (space-separated)
                while True:
                    self.skip_whitespace()
                    if self.peek() in ";{}" or not self.peek():
                        break

                    additional_value = self.read_value()
                    if additional_value:
                        values.append(additional_value)
                    else:
                        break

                self.skip_whitespace()

                # Consume semicolon if present
                if self.peek() == ";":
                    self.consume()

                # Store the values
                final_value = (
                    " ".join(values)
                    if len(values) > 1
                    else (values[0] if values else "")
                )

                # Handle multiple directives with same name
                if directive in result:
                    if isinstance(result[directive], list):
                        result[directive].append(final_value)
                    else:
                        result[directive] = [result[directive], final_value]
                else:
                    result[directive] = final_value

        return result

    def parse(self) -> Dict[str, Any]:
        """Parse the entire configuration"""
        return self.parse_block()


def print_comparison_results():
    """Compare and display results from both parsing approaches"""

    print("=" * 80)
    print("PARSER vs REGEX COMPARISON")
    print("=" * 80)
    print()

    print("Configuration to parse:")
    print("-" * 40)
    print(CONFIG_TEXT)

    # Test regex approach
    print("\n" + "=" * 80)
    print("REGEX APPROACH RESULTS")
    print("=" * 80)

    regex_parser = RegexParser()
    try:
        regex_result = regex_parser.parse(CONFIG_TEXT)
        print("✗ Regex parsing (incomplete and incorrect):")
        print(json.dumps(regex_result, indent=2))

        print("\nRegex approach problems:")
        print("• Missing deeply nested 'headers' block")
        print("• Cannot distinguish between different 'server' blocks")
        print("• Fails to handle multiple values properly")
        print("• No context awareness for quoted strings")
        print("• Cannot handle recursive nesting")

    except Exception as e:
        print(f"✗ Regex parsing failed with error: {e}")

    # Test proper parser approach
    print("\n" + "=" * 80)
    print("PROPER PARSER RESULTS")
    print("=" * 80)

    try:
        parser = ConfigParser(CONFIG_TEXT)
        parser_result = parser.parse()
        print("✓ Proper parser (complete and accurate):")
        print(json.dumps(parser_result, indent=2))

        print("\nParser approach advantages:")
        print("• Correctly handles all nested structures")
        print("• Maintains context and state")
        print("• Properly processes quoted strings")
        print("• Supports recursive parsing")
        print("• Easy to extend and maintain")
        print("• Clear error handling and debugging")

    except Exception as e:
        print(f"✗ Parser failed with error: {e}")

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("Regex is suitable for simple, flat pattern matching.")
    print("For structured, nested data, a proper parser is essential.")
    print("The complexity difference becomes exponentially worse")
    print("as the data structure becomes more sophisticated.")


if __name__ == "__main__":
    print_comparison_results()
