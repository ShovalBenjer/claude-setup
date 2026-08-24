# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of claude-setup seriously. If you believe you have found a security vulnerability in this repository, please report it responsibly.

**Please do not report security vulnerabilities through public GitHub issues, discussions, or pull requests.**

Instead, please send a detailed report to the repository maintainer via direct communication. Include the following information:

- A description of the vulnerability and its potential impact
- Steps to reproduce the issue
- Any relevant proof-of-concept code or screenshots
- Your contact information for follow-up questions

You should expect an acknowledgment within 5 business days. We will investigate and provide a more detailed response within 10 business days indicating the next steps.

## Disclosure Policy

- We follow coordinated responsible disclosure.
- Once a vulnerability is confirmed, we will work on a fix and release a patched version as quickly as possible.
- We will publicly disclose the vulnerability after a fix is available, crediting the reporter unless anonymity is requested.
- We ask that you do not publicly disclose the vulnerability until we have had a chance to address it.

## Security Best Practices

When working with this repository:

- Never commit secrets, API keys, tokens, or credentials to version control.
- Use `.env` files for local development and ensure `.env` is listed in `.gitignore`.
- Review `tools/gate/gate.py` for the secret-scan domain before submitting changes.
- Rotate any exposed credentials immediately and report the exposure.
