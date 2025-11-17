# Prompt Injection Shortcuts - Usage Guide

## Overview

The Prompt Injection feature allows you to quickly inject powerful, proven phrases into your prompts using the `:` prefix followed by TAB completion. This helps you get better, more accurate responses without typing long instructions every time.

## How to Use

### Basic Usage

1. **Type `:` followed by a category name** (or partial name)
2. **Press TAB** to see available categories
3. **Select a category** from the dropdown
4. **Press Enter** to insert a random phrase from that category

### Example

```
❯ Please help me debug this code :code
```

After pressing TAB after `:code`, you'll see:
- 💻 code - Code quality and correctness
- 🚀 combo - Powerful combined prompts
- etc.

When you select `code` and press Enter, it becomes:
```
❯ Please help me debug this code 💻 Review the code for bugs and security issues.
```

Each time you use `:code`, you'll get a different phrase randomly selected from that category!

## Available Categories

### 🧠 reasoning
**Purpose:** Improve reasoning and accuracy

**Sample phrases:**
- "Think step by step before answering."
- "Show your complete reasoning process."
- "Break this into smaller, manageable steps."

### 🔍 correction
**Purpose:** Fix or improve incorrect answers

**Sample phrases:**
- "Review your previous response for any errors."
- "Identify and correct any logical inconsistencies."
- "Re-evaluate your answer with fresh perspective."

### ✨ clarity
**Purpose:** Improve quality and clarity

**Sample phrases:**
- "Explain this clearly and concisely."
- "Use simple, straightforward language."
- "Structure your response with clear sections."

### 🎯 format
**Purpose:** Control output format

**Sample phrases:**
- "Respond using only valid JSON format."
- "Provide the answer as a numbered list."
- "Format this as a markdown table."

### 🎭 tone
**Purpose:** Adjust tone and expertise level

**Sample phrases:**
- "Explain as if I'm a complete beginner."
- "Answer with senior engineer expertise."
- "Use a neutral, professional tone."

### 🛠️ reliability
**Purpose:** Improve reliability and reduce hallucinations

**Sample phrases:**
- "State 'I'm not certain' if unsure about anything."
- "Use only verified, factual information."
- "List all assumptions you're making."

### 💻 code
**Purpose:** Code quality and correctness

**Sample phrases:**
- "Review the code for bugs and security issues."
- "Follow best practices and design patterns."
- "Add comprehensive error handling."

### 🔬 analysis
**Purpose:** Deep analysis and thorough investigation

**Sample phrases:**
- "Provide a comprehensive analysis."
- "Examine all relevant factors and trade-offs."
- "Compare different approaches systematically."

### ⚡ efficiency
**Purpose:** Quick, efficient responses

**Sample phrases:**
- "Provide just the essential information."
- "Skip explanations, give direct answers only."
- "Be as concise as possible."

### 🚀 combo
**Purpose:** Powerful combined prompts for maximum effectiveness

**Sample phrases:**
- "Think step by step and explain your reasoning clearly."
- "Review for errors, then provide a corrected response."
- "Analyze the problem, identify mistakes, then generate an improved solution."

## Advanced Usage

### Multiple Categories in One Prompt

You can use multiple categories in a single prompt:

```
❯ :reasoning Analyze this algorithm and :code provide an optimized version
```

This becomes:
```
❯ 🧠 Break this into smaller, manageable steps. Analyze this algorithm and 💻 Optimize for readability and maintainability. provide an optimized version
```

### Combining with @ File References

You can combine prompt injections with file references:

```
❯ :code Review this @src/main.py :reliability and check for issues
```

## Customization

The prompt injection phrases are stored in `data/prompt_injections.yaml`. You can:

1. **Add new categories** by adding sections to the YAML file
2. **Add new phrases** to existing categories
3. **Modify existing phrases** to better suit your needs
4. **Change emojis** for categories

### Example YAML structure:

```yaml
prompt_injections:
  my_custom_category:
    emoji: "🎨"
    description: "Custom category for design"
    phrases:
      - "Focus on user experience."
      - "Consider accessibility best practices."
      - "Ensure responsive design."
```

## Tips for Best Results

1. **Use `:reasoning`** when you need the AI to think more carefully
2. **Use `:correction`** when you got an answer that seems off
3. **Use `:clarity`** when responses are too complex or verbose
4. **Use `:code`** for programming tasks to ensure quality
5. **Use `:combo`** when you want maximum accuracy and thoroughness
6. **Use `:efficiency`** when you just need a quick, direct answer

## Auto-Iteration Boost 🍒

**The Cherry on the Cake!**

When vuhitra-cli's auto-iteration feature detects a response with a 0 rating (out of context), it automatically retries with increased anti-pattern learning. As an extra boost, **a random reasoning phrase is automatically injected** into the retry prompt!

This happens automatically—you don't need to do anything. The system will:

1. Detect the poor response (rating = 0)
2. Ask if you want to retry
3. **Automatically inject a reasoning prompt** (e.g., "🧠 Think step by step before answering.")
4. Retry with both the reasoning boost AND increased negative pattern weights

This significantly improves the chances of getting a better response on the retry!

### Example Flow:

```
❯ What is the solution to this complex problem?
[Response gets rating 0 - out of context]

⚠️  Response out of context (attempt 1/5)
Retry with increased anti-pattern learning? (Y/n) [auto in 10s]: y

🔄 Retrying (iteration 2/5) with negative_weight_boost=0.30
🍒 Auto-iteration boost: Added reasoning prompt - 'Break this into smaller, manageable steps.'
[Gets better response with reasoning guidance]
```

## Technical Details

- **Randomization:** Each time you use a category, a random phrase is selected from that category's phrase list
- **Emojis:** Emojis are added before the phrase to make it visually distinct
- **Pattern:** The feature detects `:word` patterns and replaces them before sending to the LLM
- **Tab Completion:** Uses the same autocomplete system as the `@` file reference feature
- **Auto-Iteration Integration:** Reasoning phrases are automatically injected during retry attempts (iteration_number > 0)

## Examples in Context

### Example 1: Debugging Code
```
❯ :reasoning Why is my function returning None? @src/utils/helper.py :code
```

### Example 2: Getting a Quick Answer
```
❯ :efficiency What's the capital of France?
```

### Example 3: Improving an Answer
```
❯ :correction Your previous response about async/await was confusing
```

### Example 4: Complex Analysis
```
❯ :analysis :reliability Compare REST vs GraphQL for my use case
```

## Keyboard Shortcuts Summary

| Action | Key |
|--------|-----|
| Trigger autocomplete | `:` then `TAB` |
| Navigate suggestions | `↑` / `↓` |
| Select suggestion | `Enter` |
| Cancel autocomplete | `Esc` |

---

**Note:** This feature is designed to save you time and improve response quality. Experiment with different categories to find what works best for your workflow!
