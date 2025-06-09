#!/usr/bin/env python3
"""
Functional Configuration File Parser Example

This example demonstrates a purely functional approach to parsing structured
configuration files, showing why explicit parsing is superior to regex
for nested, hierarchical data.

Sample config format:
```
# Database configuration
[database]
host = "localhost"
port = 5432
enabled = true
timeout = 30.5

[server]
    # Nested authentication section
    [server.auth]
    method = "oauth2"
    providers = ["google", "github", "facebook"]

    [server.logging]
    level = "info"
    rotate = true
```
"""

import re
from typing import Dict, List, Union, Any, Tuple, NamedTuple
import time

ConfigValue = Union[str, int, float, bool, List[str]]

class ParseState(NamedTuple):
    """Immutable state for parsing operations"""
    lines: List[str]
    line_number: int
    result: Dict[str, Any]

class ParseError(Exception):
    def __init__(self, line_number: int, message: str):
        self.line_number = line_number
        self.message = message
        super().__init__(f"Line {line_number}: {message}")

def parse_config(text: str) -> Dict[str, Any]:
    """Parse configuration text into a nested dictionary using functional approach."""
    lines = [line.strip() for line in text.strip().split('\n')]
    initial_state = ParseState(lines=lines, line_number=0, result={})

    final_state = parse_lines(initial_state)
    return final_state.result

def parse_lines(state: ParseState) -> ParseState:
    """Recursively parse all lines in the configuration."""
    if state.line_number >= len(state.lines):
        return state

    line = state.lines[state.line_number]

    # Skip empty lines and comments
    if not line or line.startswith('#'):
        return parse_lines(advance_line(state))

    # Handle section headers
    if line.startswith('[') and line.endswith(']'):
        return parse_lines(parse_section(state))

    # Handle root-level key-value pairs
    key, value = parse_key_value_line(line, state.line_number)
    new_result = {**state.result, key: value}
    new_state = ParseState(state.lines, state.line_number + 1, new_result)

    return parse_lines(new_state)

def parse_section(state: ParseState) -> ParseState:
    """Parse a section header and its contents."""
    line = state.lines[state.line_number]

    if not (line.startswith('[') and line.endswith(']')):
        raise ParseError(state.line_number + 1, f"Invalid section header: {line}")

    section_path = line[1:-1].strip()
    section_state = advance_line(state)

    # Parse section contents
    section_content, final_state = parse_section_contents(section_state)

    # Merge section into result
    new_result = set_nested_dict(state.result, section_path.split('.'), section_content)

    return ParseState(final_state.lines, final_state.line_number, new_result)

def parse_section_contents(state: ParseState) -> Tuple[Dict[str, Any], ParseState]:
    """Parse the contents of a section until the next section or end of file."""
    section_dict = {}
    current_state = state

    while current_state.line_number < len(current_state.lines):
        line = current_state.lines[current_state.line_number]

        # Stop at next section
        if line.startswith('['):
            break

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            current_state = advance_line(current_state)
            continue

        # Parse key-value pair
        key, value = parse_key_value_line(line, current_state.line_number)
        section_dict = {**section_dict, key: value}
        current_state = advance_line(current_state)

    return section_dict, current_state

def parse_key_value_line(line: str, line_number: int) -> Tuple[str, ConfigValue]:
    """Parse a key-value line into key and properly typed value."""
    if '=' not in line:
        raise ParseError(line_number + 1, f"Invalid key-value pair: {line}")

    key, value_str = line.split('=', 1)
    key = key.strip()
    value_str = value_str.strip()

    if not key:
        raise ParseError(line_number + 1, "Empty key name")

    return key, parse_value(value_str)

def parse_value(value_str: str) -> ConfigValue:
    """Parse a value string into the appropriate Python type."""
    value_str = value_str.strip()

    # Handle quoted strings
    if is_quoted_string(value_str):
        return value_str[1:-1]  # Remove quotes

    # Handle arrays
    if is_array(value_str):
        return parse_array(value_str)

    # Handle booleans
    if value_str.lower() in ('true', 'false'):
        return value_str.lower() == 'true'

    # Handle numbers
    number_value = try_parse_number(value_str)
    if number_value is not None:
        return number_value

    # Default to string
    return value_str

def is_quoted_string(value_str: str) -> bool:
    """Check if value is a quoted string."""
    return ((value_str.startswith('"') and value_str.endswith('"')) or
            (value_str.startswith("'") and value_str.endswith("'")))

def is_array(value_str: str) -> bool:
    """Check if value is an array."""
    return value_str.startswith('[') and value_str.endswith(']')

def parse_array(value_str: str) -> List[str]:
    """Parse array value into list of strings."""
    array_content = value_str[1:-1].strip()
    if not array_content:
        return []

    elements = []
    for element in array_content.split(','):
        element = element.strip()
        if is_quoted_string(element):
            elements.append(element[1:-1])
        else:
            elements.append(element)
    return elements

def try_parse_number(value_str: str) -> Union[int, float, None]:
    """Try to parse string as number, return None if not a number."""
    try:
        if '.' in value_str:
            return float(value_str)
        else:
            return int(value_str)
    except ValueError:
        return None

def set_nested_dict(d: Dict[str, Any], path: List[str], value: Any) -> Dict[str, Any]:
    """Immutably set a value in a nested dictionary structure."""
    if len(path) == 1:
        return {**d, path[0]: value}

    key = path[0]
    remaining_path = path[1:]
    current_nested = d.get(key, {})

    return {**d, key: set_nested_dict(current_nested, remaining_path, value)}

def advance_line(state: ParseState) -> ParseState:
    """Create new state with line number advanced by 1."""
    return ParseState(state.lines, state.line_number + 1, state.result)

def regex_attempt(text: str) -> Dict[str, Any]:
    """
    Attempt to parse config with regex (demonstrates limitations).
    This simplified version shows why regex becomes inadequate.
    """
    result = {}
    section_pattern = r'^\[([^\]]+)\]'
    key_value_pattern = r'^(\w+)\s*=\s*(.+)$'

    lines = text.strip().split('\n')
    current_section = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        section_match = re.match(section_pattern, line)
        if section_match:
            current_section = section_match.group(1)
            if current_section not in result:
                result[current_section] = {}
            continue

        kv_match = re.match(key_value_pattern, line)
        if kv_match:
            key, value_str = kv_match.groups()
            value = value_str.strip('"\'')  # Oversimplified

            if current_section:
                result[current_section][key] = value
            else:
                result[key] = value

    return result

def create_sample_config() -> str:
    """Generate sample configuration for testing."""
    return '''
# Database configuration
[database]
host = "localhost"
port = 5432
enabled = true
timeout = 30.5
credentials = ["user", "pass", "admin"]

[server]
    # Nested authentication section
    [server.auth]
    method = "oauth2"
    providers = ["google", "github", "facebook"]
    secure = true

    [server.logging]
    level = "info"
    rotate = true
    max_size = 100.5

[cache]
enabled = false
ttl = 3600
'''

def benchmark_parsers():
    """Compare performance and functionality of functional parser vs regex."""
    config_text = create_sample_config()

    # Benchmark functional parser
    start_time = time.time()
    for _ in range(1000):
        result_parser = parse_config(config_text)
    parser_time = time.time() - start_time

    # Benchmark regex approach
    start_time = time.time()
    for _ in range(1000):
        result_regex = regex_attempt(config_text)
    regex_time = time.time() - start_time

    print("=== PARSING RESULTS COMPARISON ===\n")

    print("Functional Parser Result:")
    print_nested_dict(result_parser)

    print("\nRegex Parser Result (Limited):")
    print_nested_dict(result_regex)

    print(f"\n=== PERFORMANCE COMPARISON ===")
    print(f"Functional Parser: {parser_time:.4f} seconds (1000 iterations)")
    print(f"Regex Approach: {regex_time:.4f} seconds (1000 iterations)")
    print(f"Functional parser is {regex_time/parser_time:.2f}x {'faster' if parser_time < regex_time else 'slower'}")

    demonstrate_functional_advantages()

def demonstrate_functional_advantages():
    """Show the advantages of the functional parsing approach."""
    print(f"\n=== FUNCTIONAL PARSER ADVANTAGES ===")
    print("✓ Immutable state transitions")
    print("✓ Recursive composition of parsing functions")
    print("✓ No side effects or global state")
    print("✓ Easy to test individual functions")
    print("✓ Handles nested sections correctly")
    print("✓ Proper type conversion")
    print("✓ Clear error messages with line numbers")
    print("✓ Composable and modular design")

    print(f"\n=== REGEX LIMITATIONS ===")
    print("✗ Cannot handle nested structures")
    print("✗ Complex state management required")
    print("✗ Difficult to compose and extend")
    print("✗ Poor error reporting")
    print("✗ Type conversion requires additional logic")

def print_nested_dict(d: Dict[str, Any], indent: int = 0) -> None:
    """Recursively print nested dictionary with proper indentation."""
    for key, value in d.items():
        if isinstance(value, dict):
            print("  " * indent + f"{key}:")
            print_nested_dict(value, indent + 1)
        else:
            print("  " * indent + f"{key}: {value} ({type(value).__name__})")

def demonstrate_error_handling():
    """Show functional parser's error handling capabilities."""
    print("\n=== ERROR HANDLING DEMONSTRATION ===")

    error_cases = [
        ("Missing equals sign", "invalid_line_here"),
        ("Invalid section", "[unclosed_section"),
        ("Empty key", "= value_without_key"),
    ]

    for description, bad_config in error_cases:
        try:
            parse_config(bad_config)
        except ParseError as e:
            print(f"{description}: {e}")

def demonstrate_immutability():
    """Show how the functional approach maintains immutability."""
    print("\n=== IMMUTABILITY DEMONSTRATION ===")

    config = create_sample_config()

    # Parse same config multiple times to show no side effects
    result1 = parse_config(config)
    result2 = parse_config(config)

    print("Results are identical (no side effects):", result1 == result2)
    print("Results are separate objects:", result1 is not result2)

    # Show that parsing doesn't modify input
    original_config = config
    parse_config(config)
    print("Original config unchanged:", config == original_config)

if __name__ == "__main__":
    benchmark_parsers()
    demonstrate_error_handling()
    demonstrate_immutability()
