# Interactive Mode UI Overhaul

This document describes the comprehensive UI overhaul for vuhitra-cli's interactive mode, introducing enhanced user experience features and verbose debugging capabilities.

## Overview

The UI overhaul includes:

1. **Auto-complete Prompt History** - Navigate and reuse previous prompts
2. **Rich Markdown Rendering** - Beautiful formatting with icons and colors
3. **Verbose Mode** - Detailed debugging output for development and troubleshooting
4. **Pretty-printed Context** - Visual display of heuristic matching and chaining
5. **Elasticsearch Insights** - View data storage operations in real-time
6. **NLP Analysis Display** - See sentiment analysis, keyword extraction, and code detection

---

## Features

### 1. Auto-complete Prompt History

The interactive mode now uses `prompt_toolkit` to provide:

- **History Navigation**: Press `↑` and `↓` to navigate through previous prompts
- **Auto-suggestions**: As you type, previous similar prompts are suggested
- **Persistent Storage**: History is saved in `~/.vuhitra/prompt_history.txt`
- **Command Completion**: Tab-completion for common commands (`exit`, `quit`, `help`, `clear`)

**Usage:**
```bash
./start.sh
>>> <press ↑ to see previous prompts>
```

---

### 2. Rich Markdown Rendering

All responses are now rendered with beautiful markdown formatting:

- **Syntax Highlighting**: Code blocks are properly highlighted
- **Styled Panels**: Prompts and responses displayed in bordered panels
- **Icons**: Visual indicators (🚀, 🤖, 👤, etc.) for different sections
- **Colors**: Syntax-aware coloring for better readability

**Example:**
```
╭─────────── 🤖 Assistant Response ───────────╮
│                                              │
│  # Example Response                          │
│                                              │
│  Here's some **formatted** markdown with:    │
│  - Bullet points                             │
│  - Code: `example_code()`                    │
│  - And more!                                 │
│                                              │
╰──────────────────────────────────────────────╯
```

---

### 3. Verbose Mode

Enable verbose mode to see detailed debugging information:

**Enable verbose mode:**
```bash
./start.sh --verbose
# or
./start.sh -v
```

**Non-interactive mode with verbose:**
```bash
./start.sh -v -p "Your prompt here"
```

**What verbose mode shows:**

#### a) Heuristic Context Retrieval
```
════════════════════════════════════════════════════════════════════════════════
📚 HEURISTIC CONTEXT RETRIEVAL
════════════════════════════════════════════════════════════════════════════════

🎯 Matched Heuristic
├── 📋 Details
│   ├── ID: abc123xyz
│   ├── Rating: ⭐⭐⭐⭐⭐ (5/5)
│   ├── Confidence: 87.5%
│   └── Word Count: 150 words
├── 🧠 NLP Analysis
│   ├── Sentiment (VADER): 0.85
│   └── Keywords: python, function, async, await, error
├── 💬 Content Preview
│   ├── Prompt: How to handle async errors in Python...
│   └── Response: You can use try-except blocks with async...
├── 🔗 Chain (2 parents)
│   ├── Parent 1
│   │   ├── ID: def456uvw
│   │   ├── Rating: ⭐⭐⭐⭐
│   │   └── Depth: 1
│   └── Parent 2
│       ├── ID: ghi789rst
│       ├── Rating: ⭐⭐⭐⭐⭐
│       └── Depth: 0
└── 📊 Scoring Breakdown
    ├── Keyword Score: 0.892
    ├── Levenshtein Score: 0.756
    ├── Semantic Score: 0.913
    └── Final Score: 0.875
```

#### b) NLP Analysis
```
════════════════════════════════════════════════════════════════════════════════
🧠 NLP ANALYSIS
════════════════════════════════════════════════════════════════════════════════

Sentiment Analysis:
  😊 VADER Score: 0.725

Extracted Keywords:
  python, async, error, handling, function, await, try, except

Code Detection:
  Is Code: ✓ Yes
  Purpose: function definition

Word Count: 42
```

#### c) Elasticsearch Operations
```
════════════════════════════════════════════════════════════════════════════════
🗄️  ELASTICSEARCH: STORE FEEDBACK
════════════════════════════════════════════════════════════════════════════════

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field                      ┃ Value                      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ prompt                     │ How to handle async err... │
│ rating                     │ 5                          │
│ prompt_sentiment_vader     │ 0.725                      │
│ prompt_keywords            │ ["python", "async", ...]   │
│ execution_time_ms          │ 1523                       │
│ chain_depth                │ 3                          │
│ parent_heuristic_id        │ abc123xyz                  │
└────────────────────────────┴────────────────────────────┘
```

#### d) Timing Information
```
⏱️  Heuristic retrieval: 234.56ms
⏱️  LLM generation: 1523.45ms
⏱️  Feedback submission: 89.12ms
⏱️  Total request: 1847.13ms
```

#### e) Debug Information
```
[DEBUG] Heuristic Retrieval Request:
{
  "endpoint": "http://localhost:18001/retrieve/similar",
  "prompt_length": 42,
  "confidence_threshold": 0.75,
  "min_rating": 3
}

[DEBUG] Enhanced Prompt:
{
  "original_length": 42,
  "enhanced_length": 198,
  "context_added": 156
}
```

---

## Architecture

### New Components

#### 1. `src/utils/ui_formatter.py`
Centralized UI formatting utilities using the `rich` library:

**Key Functions:**
- `set_verbose_mode(enabled)` - Set global verbose mode
- `print_banner(model)` - Display styled banner
- `print_response(response)` - Render markdown response
- `print_context_verbose(data)` - Pretty-print heuristic context
- `print_elasticsearch_verbose(operation, data)` - Display ES operations
- `print_nlp_analysis_verbose(analysis)` - Show NLP results
- `print_timing_verbose(operation, duration)` - Display timing info
- `print_error/warning/success/info(message)` - Styled messages
- `print_debug(title, data)` - Debug output with JSON syntax highlighting

**Global State:**
- `_verbose_mode` - Boolean flag set once at startup
- `console` - Rich Console instance for all output

#### 2. `src/utils/prompt_history.py`
Prompt history management with auto-complete:

**Class: `PromptHistoryManager`**

**Features:**
- File-based history persistence (`~/.vuhitra/prompt_history.txt`)
- Auto-suggest from history
- Keyboard navigation (↑/↓)
- Command completion
- Styled prompt with custom colors

**Methods:**
- `get_prompt()` - Get user input with history/auto-complete
- `clear_history()` - Clear history file
- `get_history_count()` - Count history items
- `get_recent_history(count)` - Get recent N items

#### 3. Enhanced `src/cli.py`

**Changes:**
- Integrated `ui_formatter` for all output
- Integrated `PromptHistoryManager` for input
- Added `verbose` parameter to all functions
- Enhanced error messages with styled output
- Timing tracking for all operations
- Metadata enrichment for feedback

**Flow with Verbose Mode:**
```python
interactive_mode(model, verbose=True)
  ↓
set_verbose_mode(True)
  ↓
print_banner(model)  # Show verbose status
  ↓
[Loop]
  get_prompt() from PromptHistoryManager
  print_user_prompt() if verbose
  fetch_similar_heuristic(verbose=True)
    → print_context_verbose() if match found
  generate()
  print_response() with markdown
  collect_feedback()
  send_feedback_to_sandbox(verbose=True)
    → print_nlp_analysis_verbose()
    → print_elasticsearch_verbose()
```

### Sandbox Service Updates

#### 1. `services/sandbox/src/main.py`

**Updated Endpoints:**

**POST `/retrieve/similar`**
- Added `verbose: bool` parameter
- Returns additional fields when verbose:
  - `chain` - Full parent heuristic chain
  - `retrieval_metadata` - Filtering statistics

**POST `/analyze/feedback`**
- Added `verbose: bool` parameter
- Synchronous processing when verbose (instead of background)
- Returns detailed analysis:
  - `nlp_analysis` - Sentiment, keywords, code detection
  - `elasticsearch_doc` - Complete stored document

#### 2. `services/sandbox/src/heuristics.py`

**Updated Class: `Heuristics`**

**New Method: `_analyze_and_store_sync()`**
- Synchronous version of `_analyze_and_store()`
- Returns complete analysis results
- Used when verbose mode is enabled

**Modified Method: `process_feedback(verbose=False)`**
- Routes to sync or async processing based on verbose flag
- Returns detailed results for verbose mode

---

## Configuration

### Dependencies

Added to `requirements.txt`:
```
rich>=13.7.0,<14.0.0
prompt-toolkit>=3.0.43,<4.0.0
```

### Installation

```bash
# Install new dependencies
./start.sh  # Automatically installs on first run

# Or manually
source venv/bin/activate
pip install -r requirements.txt
```

---

## Usage Examples

### Basic Interactive Mode (Non-Verbose)
```bash
./start.sh

# Beautiful UI with markdown rendering
# Prompt history with auto-complete
# Clean, minimal output
```

### Verbose Interactive Mode
```bash
./start.sh --verbose

# Everything from basic mode, plus:
# - Heuristic matching details
# - NLP analysis results
# - Elasticsearch operations
# - Timing information
# - Debug logs
```

### Non-Interactive with Verbose
```bash
./start.sh -v -p "How do I use async/await in Python?"

# Single prompt with full debugging output
# Useful for troubleshooting
```

### History Navigation
```bash
./start.sh
>>> <type partial prompt>
# Auto-suggestion appears in gray
# Press → to accept suggestion
# Press ↑/↓ to navigate history
```

---

## Benefits

### For Users

1. **Better Experience**
   - Beautiful, readable output with markdown
   - Easy access to previous prompts
   - Visual feedback on all operations

2. **Better Insights**
   - See what context influenced the response
   - Understand confidence scores
   - Track performance metrics

### For Developers

1. **Easier Debugging**
   - Verbose mode shows all internal operations
   - NLP analysis visible
   - Elasticsearch operations transparent
   - Timing helps identify bottlenecks

2. **Better Development**
   - Rich formatting makes logs readable
   - Structured debug output
   - Clear error messages with context

---

## Technical Notes

### Thread Safety
- Verbose mode uses synchronous processing for immediate feedback
- Non-verbose mode maintains async background processing
- No race conditions or blocking issues

### Performance
- Verbose mode adds minimal overhead (~50-100ms for formatting)
- History auto-complete is instant (file-based, cached by prompt_toolkit)
- Rich rendering is lazy (only renders visible content)

### Backwards Compatibility
- All changes are backwards compatible
- Verbose mode is opt-in
- Default behavior unchanged for non-verbose mode
- API contracts maintained for sandbox endpoints

---

## Future Enhancements

Potential improvements:

1. **Configurable Themes**
   - Allow users to customize colors
   - Dark/light theme support

2. **Export Features**
   - Export session history with responses
   - Save verbose logs to file

3. **Interactive Heuristic Explorer**
   - Browse stored heuristics interactively
   - Search and filter capabilities

4. **Performance Profiling**
   - Detailed breakdown of LLM vs context retrieval
   - Historical performance tracking

5. **Rich Tables for Chain Display**
   - Tabular view of heuristic chains
   - Sortable columns

---

## Troubleshooting

### Prompt History Not Working
```bash
# Check history file exists
ls ~/.vuhitra/prompt_history.txt

# Clear and restart
rm ~/.vuhitra/prompt_history.txt
./start.sh
```

### Verbose Output Not Showing
```bash
# Ensure flag is set correctly
./start.sh --verbose  # correct
./start.sh -verbose   # incorrect (single dash)

# Check in code:
python -c "from src.utils.ui_formatter import is_verbose; print(is_verbose())"
```

### Markdown Not Rendering
```bash
# Ensure rich is installed
pip list | grep rich

# Reinstall if needed
pip install --upgrade rich
```

### Sandbox Not Returning Verbose Data
```bash
# Check sandbox is running
curl http://localhost:18001/health

# Check request includes verbose flag
# (Enable verbose mode to see request debug output)
./start.sh -v
```

---

## Contributing

When extending the UI:

1. **Use ui_formatter functions** - Don't print directly
2. **Check verbose mode** - Use `is_verbose()` before expensive operations
3. **Add timing** - Use `print_timing_verbose()` for new operations
4. **Document** - Update this file with new features
5. **Test both modes** - Ensure verbose and non-verbose work correctly

---

## Credits

- **Rich Library**: https://github.com/Textualize/rich
- **Prompt Toolkit**: https://github.com/prompt-toolkit/python-prompt-toolkit

---

*Last Updated: 2025-11-14*
