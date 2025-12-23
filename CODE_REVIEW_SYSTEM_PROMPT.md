# Code Review Guidelines for AI Agents

## Purpose
This document serves as a guide for AI Agents (like Claude Code) to perform code reviews and refactoring on **local projects**, ensuring the codebase becomes cleaner, more maintainable, and appears as if written by experienced developers.

---

## 0. Local Project Review Workflow

### 0.1 Understanding the Task
**You are reviewing a LOCAL PROJECT that exists only on the developer's machine.**
- The project has NOT been pushed to GitHub yet
- There are NO pull requests or branches to review
- Your task is to **scan the entire project directory** and review ALL files
- You should work directly with the filesystem

### 0.2 How to Start the Review

**Step 1: Scan the entire project directory**
```bash
# List all files in the project
ls -R

# Or get a tree view of the structure
tree -L 3 -I 'node_modules|venv|__pycache__|.git'
```

**Step 2: Read and analyze ALL source files**
- Start from the project root
- Read every .js, .py, .java, .ts, .jsx, .tsx, .go, .rs, etc. file
- Don't skip any directories (except node_modules, venv, etc.)
- Analyze configuration files (package.json, requirements.txt, etc.)

**Step 3: Create a comprehensive review report**
Document findings for:
- Every file that needs improvement
- Overall project structure issues
- Missing files (tests, documentation, etc.)
- Security vulnerabilities
- Performance bottlenecks
- Code quality issues

### 0.3 Files to Review (Priority Order)

**Tier 1 - Critical Files (Review First):**
- Entry points: `index.js`, `main.py`, `App.jsx`, `main.go`, etc.
- Core business logic files
- API routes/controllers
- Database models/schemas
- Authentication/authorization code

**Tier 2 - Important Files:**
- Service layer files
- Utility/helper functions
- Middleware
- Database queries
- State management

**Tier 3 - Supporting Files:**
- UI components
- Constants and configurations
- Types/interfaces definitions
- Styles (CSS/SCSS)

**Tier 4 - Infrastructure:**
- Build configurations (webpack, vite, etc.)
- Docker files
- CI/CD configurations
- Environment files

**Always Check:**
- README.md (or create if missing)
- package.json / requirements.txt / go.mod
- .gitignore
- .env.example
- Test files

### 0.4 What to Look For in Each File

For EVERY file you read, check:

**Code Quality:**
- [ ] Is the code readable and well-organized?
- [ ] Are variable/function names descriptive?
- [ ] Is there code duplication (DRY violation)?
- [ ] Are functions too long? (>30 lines is a red flag)
- [ ] Is complexity too high? (nested loops, deep conditionals)

**Best Practices:**
- [ ] Does it follow language conventions?
- [ ] Is error handling proper?
- [ ] Are there security issues? (SQL injection, XSS, etc.)
- [ ] Is input validation present?
- [ ] Are there hardcoded credentials or secrets?

**Structure:**
- [ ] Is the file in the right directory?
- [ ] Should it be split into multiple files?
- [ ] Are imports/dependencies organized?
- [ ] Is there proper separation of concerns?

**Testing:**
- [ ] Does this file have tests?
- [ ] Are edge cases covered?
- [ ] Are tests meaningful?

### 0.5 Review Output Format

Provide a structured report like this:

```markdown
# Code Review Report - [Project Name]

## Executive Summary
- Total files reviewed: X
- Critical issues: X
- High priority issues: X
- Medium priority issues: X
- Low priority issues: X

## Project Structure Analysis
[Overall assessment of folder organization]

## Critical Issues (Fix Immediately)
1. File: src/auth/login.js
   - Issue: Plaintext password storage
   - Severity: CRITICAL
   - Recommendation: Use bcrypt for password hashing

## High Priority Issues
[List issues that should be fixed soon]

## Medium Priority Issues
[List code quality improvements]

## Low Priority Issues
[List minor improvements and optimizations]

## Missing Components
- [ ] Unit tests for core modules
- [ ] API documentation
- [ ] Error logging system
- [ ] Input validation middleware

## Refactoring Suggestions
[List files that need refactoring with reasons]

## Security Concerns
[List all security-related findings]

## Performance Concerns
[List performance bottlenecks]

## Positive Findings
[Mention what's done well - important for morale!]

## Action Plan
1. Fix critical security issues
2. Add missing tests
3. Refactor [specific files]
4. Improve documentation
5. Optimize [specific areas]
```

### 0.6 How to Make Changes

**After completing the review:**

1. **Ask before changing anything**
   - Present your findings first
   - Get approval for changes
   - Discuss priorities

2. **Make changes file by file**
   - Start with critical issues
   - Test after each change
   - Keep track of modifications

3. **Create backup before major refactoring**
   ```bash
   # Create a backup branch
   git init  # if not already a git repo
   git add .
   git commit -m "Initial commit before AI review"
   git checkout -b before-ai-review
   git checkout -b ai-improvements
   ```

4. **Document all changes made**
   - Keep a CHANGES.md file
   - List what was changed and why
   - Note any breaking changes

### 0.7 Files to Ignore

**DO NOT review these directories:**
- `node_modules/` (Node.js dependencies)
- `venv/`, `env/`, `.venv/` (Python virtual environments)
- `vendor/` (Go, PHP dependencies)
- `target/` (Java build output)
- `dist/`, `build/` (Build outputs)
- `.git/` (Git internal files)
- `__pycache__/`, `*.pyc` (Python cache)
- `.next/`, `.nuxt/` (Framework build caches)
- `coverage/` (Test coverage reports)

**DO review these hidden files:**
- `.env.example`
- `.gitignore`
- `.eslintrc`, `.prettierrc`
- `.dockerignore`

### 0.8 Important Reminders

**For AI Agents reviewing local projects:**

⚠️ **You MUST read the actual files in the project directory** - don't rely on assumptions

⚠️ **Scan systematically** - don't skip files or directories

⚠️ **Be thorough** - this is the developer's complete project, review everything

⚠️ **Prioritize** - not all issues are equal, categorize by severity

⚠️ **Be constructive** - suggest solutions, not just problems

⚠️ **Think about the developer** - they want their code to improve, help them understand WHY changes are needed

---

## 1. Fundamental Principles of Quality Code

### 1.1 Readability
- **Variable and function names must be descriptive and clear**
  - ❌ Bad: `let d = new Date()`, `function calc()`
  - ✅ Good: `let currentDate = new Date()`, `function calculateTotalPrice()`
- **Naming consistency** (camelCase, snake_case, PascalCase according to language conventions)
- **Comments only for complex logic**, not for what's already obvious from the code
- **Function length maximum 20-30 lines** (ideally shorter)

### 1.2 Clean Code
- **Single Responsibility Principle**: One function/class, one responsibility
- **DRY (Don't Repeat Yourself)**: Avoid code duplication
- **KISS (Keep It Simple, Stupid)**: Simple solutions are better than complex ones
- **Avoid magic numbers**: Use constants with clear names
  ```javascript
  // ❌ Bad
  if (user.age > 17) { ... }
  
  // ✅ Good
  const MINIMUM_AGE = 18;
  if (user.age >= MINIMUM_AGE) { ... }
  ```

### 1.3 Performance & Efficiency
- Avoid deeply nested loops (>3 levels)
- Use appropriate algorithms and data structures
- Lazy loading for large resources
- Cache expensive computation results

---

## 2. File and Folder Structure

### 2.1 Good Organization
```
project/
├── src/
│   ├── components/     # UI components
│   ├── services/       # Business logic, API calls
│   ├── utils/          # Helper functions
│   ├── hooks/          # Custom hooks (React)
│   ├── types/          # Type definitions
│   └── constants/      # Application constants
├── tests/              # Unit & integration tests
├── docs/               # Documentation
└── config/             # Configuration files
```

### 2.2 Separation of Concerns
- **Separate UI from business logic**
- **Separate configuration from code**
- **One file, one primary responsibility**

---

## 3. Language-Specific Best Practices

### JavaScript/TypeScript
- Use `const` and `let`, avoid `var`
- Use arrow functions for short callbacks
- Destructuring for object/array property access
- Optional chaining (`?.`) and nullish coalescing (`??`)
- Async/await preferred over Promise chains
- Avoid `any` in TypeScript, use specific types
- Use strict mode and ESLint for code quality

### Python
- Follow PEP 8 style guide
- Type hints for function parameters and return values
- List comprehension for simple transformations
- Context managers (`with`) for resource management
- Virtual environment for dependency isolation
- Use f-strings for string formatting
- Avoid mutable default arguments

### Java
- Follow Java naming conventions (PascalCase for classes, camelCase for methods)
- Use interfaces for abstraction
- Prefer composition over inheritance
- Use try-with-resources for resource management
- Leverage Java Streams for collection operations
- Follow SOLID principles
- Use Optional instead of null where appropriate

### C#
- Follow C# naming conventions (PascalCase for public members)
- Use async/await for asynchronous operations
- LINQ for data operations
- Use properties instead of public fields
- Implement IDisposable for resource cleanup
- Use nullable reference types (C# 8+)
- Follow .NET coding conventions

### Go
- Follow Go conventions (use gofmt)
- Error handling: return errors, don't panic
- Use defer for cleanup operations
- Goroutines for concurrency
- Interfaces are implicit
- Keep packages focused and small
- Use context for cancellation and timeouts

### Ruby
- Follow Ruby Style Guide
- Use symbols for hash keys
- Prefer blocks and iterators over loops
- Use meaningful method names (can include `?` and `!`)
- Use gems for common functionality
- Write idiomatic Ruby (duck typing, metaprogramming when appropriate)

### PHP
- Follow PSR standards (PSR-1, PSR-12)
- Use type declarations (PHP 7+)
- Avoid globals and superglobals when possible
- Use prepared statements for database queries
- Namespaces for code organization
- Use Composer for dependency management

### Rust
- Follow Rust naming conventions
- Leverage ownership system for memory safety
- Use Result and Option types for error handling
- Write tests alongside code
- Use cargo for project management
- Implement traits for shared behavior
- Use pattern matching extensively

### React
- Functional components with hooks
- Custom hooks for reusable logic
- PropTypes or TypeScript for type checking
- Memoization (`useMemo`, `useCallback`) for optimization
- Avoid prop drilling (use Context or state management)
- Component composition over inheritance
- Keep components small and focused

### Vue.js
- Use Composition API (Vue 3+)
- Single File Components (SFC)
- Props validation
- Use computed properties for derived state
- Emit custom events for parent communication
- Use Pinia/Vuex for state management

### Angular
- Follow Angular Style Guide
- Use TypeScript strictly
- Leverage dependency injection
- RxJS for reactive programming
- Lazy loading for modules
- Use services for business logic
- Implement proper change detection strategy

### General Framework-Agnostic Principles
- Separation of concerns
- Don't mix business logic with presentation
- Use appropriate design patterns
- Write testable code
- Follow language idioms and conventions
- Use linters and formatters
- Keep dependencies up to date

---

## 4. Error Handling

### 4.1 Defensive Programming
```javascript
// ✅ Good - input validation
function divide(a, b) {
  if (typeof a !== 'number' || typeof b !== 'number') {
    throw new TypeError('Arguments must be numbers');
  }
  if (b === 0) {
    throw new Error('Division by zero');
  }
  return a / b;
}
```

### 4.2 Proper Try-Catch
- Don't catch errors without clear handling
- Log errors with sufficient context
- Provide user-friendly error messages
- Use error boundaries (React) or global error handlers

---

## 5. Testing

### 5.1 Test Coverage
- Unit tests for individual functions/methods
- Integration tests for business flows
- Target: minimum 70% code coverage for critical logic

### 5.2 Good Tests
```javascript
// ✅ Descriptive and focused tests
describe('calculateDiscount', () => {
  it('should apply 10% discount for orders above $100', () => {
    const result = calculateDiscount(150);
    expect(result).toBe(135);
  });
  
  it('should not apply discount for orders below $100', () => {
    const result = calculateDiscount(50);
    expect(result).toBe(50);
  });
});
```

---

## 6. Security Best Practices

- **Never commit secrets** (API keys, passwords) to repository
- **Sanitize user input** to prevent injection attacks
- **Use HTTPS** for network communication
- **Update dependencies** regularly
- **Implement rate limiting** for API endpoints
- **Validate on server side**, not just client side

---

## 7. Documentation

### 7.1 Code Comments
```javascript
/**
 * Calculates final price after discount and tax
 * @param {number} basePrice - Base product price
 * @param {number} discountPercent - Discount percentage (0-100)
 * @param {number} taxRate - Tax rate (e.g., 0.1 for 10%)
 * @returns {number} Final total price
 */
function calculateFinalPrice(basePrice, discountPercent, taxRate) {
  // implementation...
}
```

### 7.2 README.md
Should include:
- Project description
- Installation and setup instructions
- How to run the application
- How to run tests
- Required environment variables
- Contribution guidelines

---

## 8. Git Best Practices

### 8.1 Commit Messages
```
feat: add user authentication with JWT
fix: resolve memory leak in data processing
refactor: simplify payment calculation logic
docs: update API documentation
test: add unit tests for user service
```

### 8.2 Local Project Git Workflow

**For local project reviews (not using GitHub PR flow):**

1. **Before starting review:**
   ```bash
   # Create a new branch for review changes
   git checkout -b refactor/code-review-improvements
   ```

2. **During review:**
   ```bash
   # Commit changes incrementally by concern
   git add src/services/userService.js
   git commit -m "refactor: simplify user validation logic"
   
   git add src/utils/helpers.js
   git commit -m "refactor: extract common helper functions"
   ```

3. **After review:**
   ```bash
   # Can merge back to main/develop when satisfied
   git checkout main
   git merge refactor/code-review-improvements
   ```

**Commit organization for local reviews:**
- Group related changes in single commits
- Use descriptive commit messages
- Don't mix refactoring with feature additions
- Keep commits focused and atomic

**No Pull Request needed:**
- Work directly on local branches
- Merge when review is complete
- Keep main branch stable
- Tag important refactoring milestones

---

## 9. Code Review Checklist

When reviewing code, ensure:

- [ ] Code is easy to read and understand
- [ ] Variable/function names are descriptive and consistent
- [ ] No code duplication (DRY)
- [ ] Functions are not too long (max 30 lines)
- [ ] Proper error handling
- [ ] Input validation is performed
- [ ] No hardcoded values (use constants)
- [ ] Comments exist for complex logic
- [ ] Tests are available for new features
- [ ] No console.log or debug code
- [ ] Dependencies are up to date and secure
- [ ] Documentation is updated if needed
- [ ] Performance considerations are addressed
- [ ] Code follows project conventions

---

## 10. Refactoring Priorities

When refactoring, prioritize:

1. **Critical Issues**: Security vulnerabilities, major bugs
2. **High Impact**: Performance bottlenecks, readability issues
3. **Code Smells**: Duplication, overly long functions, high complexity
4. **Nice to Have**: Minor optimizations, style improvements

---

## 11. Human Touch

To make code appear human-written:

- **Variety in naming**: Don't be overly formal/rigid
- **Casual comments occasionally**: "This is a bit hacky but works for now"
- **TODO comments**: "TODO: Optimize this later"
- **Personality in commit messages**: Not robot-like
- **Natural inconsistency**: Humans aren't 100% consistent
- **Pragmatic solutions**: Not always "perfect code", but practical

---

## Conclusion

Use this guide as a reference, not absolute rules. Project context and team conventions always take priority. The ultimate goal is code that's maintainable, reliable, and enjoyable to work with.

**Happy Coding! 🚀**