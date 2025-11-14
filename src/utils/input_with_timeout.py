"""
Input with Timeout Utility

Provides a function to get user input with a timeout, useful for auto-iteration prompts.
"""
import sys
import select


def input_with_timeout(prompt: str, timeout_seconds: int = 3, default: str = 'Y') -> str:
    """
    Get user input with a timeout. If the user doesn't respond within the timeout,
    return the default value.

    Args:
        prompt: The prompt message to display to the user
        timeout_seconds: Maximum seconds to wait for user input (default: 3)
        default: Default value to return if timeout occurs (default: 'Y')

    Returns:
        User input string or default value if timeout

    Example:
        >>> response = input_with_timeout("Retry? (Y/n) [auto in 3s]: ", 3, 'Y')
        >>> if response.lower() == 'y':
        >>>     print("Retrying...")
    """
    print(prompt, end='', flush=True)

    # Use select to wait for input with timeout (works on Linux/Unix)
    # On Windows, this fallback to immediate input without timeout
    try:
        # select() works on Unix/Linux/Mac
        ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)

        if ready:
            # User provided input before timeout
            user_input = sys.stdin.readline().strip()
            return user_input if user_input else default
        else:
            # Timeout occurred, use default
            print(f"\n(timeout - using default: {default})")
            return default

    except (OSError, AttributeError):
        # Fallback for Windows or other systems where select doesn't work on stdin
        # In this case, we can't implement timeout easily, so just get input normally
        print(f" [timeout not supported on this system, press Enter for default '{default}']")
        user_input = input().strip()
        return user_input if user_input else default
