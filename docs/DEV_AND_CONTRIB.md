# Pychub Development and Contribution Guide

Oh! You are here to learn how to contribute to Pychub? Or, at least, you are
curious about one or more of the following:

- how Pychub works
- how it is built
- how it is tested
- how it is packaged
- why it behaves the way it does
- how you can debug something

Maybe you just want to poke around. That's great, and you are in the right
place. Welcome! We are glad you are here.

## Requirements

While pychub can run on any Python >= 3.9, it is recommended to use Python 3.11
or newer for development. Pychub development also requires the following:

- [`pip`](https://pip.pypa.io/en/stable/) (should ship with Python)
- [`poetry`](https://python-poetry.org/) (for project management)

Check the links above, or consult the documentation for your OS or distribution
for more information.

## Development Environment Setup

If you have not already cloned the pychub repository, please do that now. In the
root directory of this repository, you will notice the `setup.sh` script. This
is a convenience script that will:

1. Check that you have the necessary version of Python
2. Check that you have the necessary python modules installed (`pip` and`poetry`)
3. Set up a project-isolated virtual environment (venv)
4. Install the necessary dependencies into the venv using `poetry install`

Once that is done, you will see a message letting you know it’s ready to go.
You can then open the project in your favorite IDE or editor and get started.

Happy developing!

## Contributing

If you are reading this with the intent to contribute, then let us first extend
our gratitude to you for your interest and generosity. Different people and teams
define "contribution" in different ways, but we think of it in fairly loose
terms. Anything from feedback, to filing an issue, to submitting a pull request
for a new feature are contributions. Time is an invaluable resource, and we
immensely appreciate that you are considering a contribution of any kind. It is
likely that any contribution that you want to make will fit into one of the
following categories.

### Discussions

If you have an idea, suggestion, or question, then you can open a discussion.
You don’t need to have a fully formed proposal. This is the space for early
thoughts, exploration, or requests for clarification. The only guideline is to
please keep it constructive and respectful.

### Issues

Do you have a request for a new feature? Is anything missing from the
documentation, or not stated clearly? These things are great candidates for
issues.

If you find a bug or something that feels unintentionally confusing or broken,
please open an issue. Even if you’re not 100% sure it’s a bug, it’s better to
report it.

There are no formal requirements or format for issues, but please try to help us
to understand what you are seeing. Some ideas to keep in mind when filing an
issue are:

- a clear description of what happened
- the steps (if any) to reproduce the problem
- environment info, if relevant (OS, Python version, etc.)
- any relevant logs or error messages

The easier it is for us to reproduce the problem, the faster we can fix it.
Either way, it is probably better to file an issue with less information than
not filing an issue at all.

### Pull Requests

Sometimes, a pull request is the most direct way to handle a concern. They can
address many things, including:

- bug fixes
- new features
- awkward/unintuitive/confusing behavior
- test coverage improvements
- documentation updates

Here are some things to keep in mind when submitting a pull request. If you can
adhere to these points, it will make everything easier:

- branch off of `main`
- add or update any applicable tests
- describe why you are requesting the change
- describe what your change does
- update documentation wherever applicable
- experimental work, and work that is likely to change, should be submitted as
  a draft pull request

Regarding the last point about experimental work: this can be a good way to
introduce an idea and get some feedback and encourage collaboration. Maybe you
have the beginnings of an idea, but you are unsure about how to proceed. This
is a great way to get feedback and help refine your idea, or to get some help
and guidance.

# What We Do With Feedback (Even the Messy Kind)

Not all feedback arrives perfectly phrased. Sometimes it’s unclear, unpolished,
or even kind of grumpy, and all of it is perfectly OK.

If someone took the time to say something, it means something created enough
of a problem that they felt they needed to speak up. That’s useful information.
We value and appreciate the information in any form. Our goal is to ask:

- “What can we learn from this?”
- “Where was the rough edge?”
- “How can we improve the experience for everyone?”

So if you have thoughts (even vague ones) or feedback that feels more like
frustration than a feature request, then please share it. We’ll do our best to
interpret it, and to turn it into something that makes things better for
everyone. We only hope that you will stick around to help us make it better. We
might ask some questions to make sure that we understand the pain points, and
we appreciate the clarification, whether it comes with fire or friendliness.

Above all, we aim to prioritize bug fixes and release them ASAP to quickly
reduce any impact on users.

# A Final Note On Contributions

Speak up. Share your thoughts. You belong here!

Whether you're a first-day beginner, a seasoned Python contributor, or somewhere
in between (like most of us), your voice matters. Good ideas and helpful
feedback don’t require mastery. They come from a willingness to share.

If you notice something confusing, have an idea to improve the experience, or
just want to ask "why does it work this way?", please speak up. You don’t need
to know the internals, or have a perfect solution in mind. In fact, many of the
best changes start with a simple question or comment from someone seeing things
with fresh eyes.

This project grows stronger through collaboration, and collaboration means
hearing from people with different perspectives, experiences, and backgrounds.

So if you’re thinking:

- “I’m probably missing something.”
- “Someone else has surely already thought of this.”
- “It’s not a big deal, so I won’t bring it up.”

Don't second guess yourself. You’re exactly the kind of person we want to hear
from.

Welcome aboard. We’re glad you’re here, and we look forward to working with you.
