<h1 align="center">Anonymous chat client</h1>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-linux-green?style=for-the-badge" />
  <img alt="Python version" src="https://img.shields.io/badge/python-3.10-green?style=for-the-badge" />
</p>

<!-- TOC -->
* [Anonymous chat client](#anonymous-chat-client)
  * [Description](#description)
  * [Installation](#installation)
  * [How to run](#how-to-run)
  * [How configure](#how-configure)
    * [Cli options](#cli-options)
    * [`settings.ini` file](#settingsini-file)
  * [Project goal](#project-goal)
<!-- TOC -->

## Description
Client for anonymous chat. Allows you to read and write messages, saves the history of correspondence.

## Installation

Install using [poetry](https://python-poetry.org/):
```bash
git clone https://github.com/savilard/chat-client.git
cd chat-client
poetry install --without dev
```

## How to run

```shell
poetry run start
```

## How configure

The script can be configured in two ways:
- command line arguments;
- file   `settings.ini`.

### Cli options

```text
- --host - host of chat. Default - 'minechat.dvmn.org';
- --outport - port to read msgs. Default - 5000;
- --inport - port to write msg. Default - 5050;
- --history - file path for recording chat history. Default - 'minechat.history';
```

### `settings.ini` file
Create a file in the root of the project and fill it out using the example:
```ini
host = 'minechat.dvmn.org'
outport = 5000
inport = 5050
history = 'minechat.history'
```

The chat connection token is created at the first startup and is saved in the .env file.


## Project goal

The code is written for educational purposes in an online course for web developers [dvmn.org](https://dvmn.org).
