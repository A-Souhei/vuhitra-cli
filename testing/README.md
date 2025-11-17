# Testing Directory

This directory contains example Python files for testing the Mirror+Vanisher Development MCP.

## Files

- **calculator.py** - Simple calculator with add, subtract, multiply, divide functions
- **string_utils.py** - String utility functions (reverse, capitalize, count vowels, palindrome check)
- **main.py** - Main application that imports and uses the above modules

## Usage

### To test the Mirror+Vanisher MCP:

1. **Mirror this directory:**
   ```bash
   /mirror do @testing
   ```

2. **Load as vanisher:**
   ```bash
   /vanisher load @testing testing "Example Python project for MCP testing"
   ```

3. **Verify it's a mirror+vanisher:**
   Use the MCP tool `verify_mirror_vanisher` with path `testing`

4. **Run MCP operations:**
   - Explore the structure
   - Detect tech stack (Python)
   - Find entrypoints (main.py)
   - Analyze architecture
   - Generate tests
   - Run quality checks
   - Run security scan

## Running the Application

```bash
cd testing
python main.py
```

Expected output:
```
=== Calculator Demo ===
10 + 5 = 15
10 - 5 = 5
10 * 5 = 50
10 / 5 = 2.0

=== String Utilities Demo ===
Original: hello world
Reversed: dlrow olleh
Capitalized: Hello World
Vowel count: 3

'A man a plan a canal Panama' is palindrome: True
```

## Example Tasks for the MCP

Try these tasks with the `create_plan` tool:

1. "Add a power function to calculator.py"
2. "Add a function to check if a string is an anagram"
3. "Fix the bug in the divide function (add better error handling)"
4. "Refactor string_utils to use a StringProcessor class"
5. "Add type hints to all functions"

## Expected MCP Workflow

For a task like "Add a power function to calculator.py":

1. **Exploration**: Discover calculator.py with 4 functions
2. **Architecture**: Identify functional programming pattern
3. **Planning**: Create plan with 4 steps (design, implement, test, document)
4. **Code Generation**: Generate diff to add power() function
5. **Testing**: Generate unit tests for power()
6. **Quality**: Run linter/formatter
7. **Security**: Check for any issues

This provides a realistic example for the MCP to demonstrate all 8 pillars of the development methodology.
