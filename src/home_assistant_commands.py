#!/usr/bin/env python3
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Run a recognizer using the Google Assistant Library.

The Google Assistant Library has direct access to the audio API, so this Python
code doesn't need to record audio. Hot word detection "OK, Google" is supported.

The Google Assistant Library can be installed with:
    env/bin/pip install google-assistant-library==0.0.2

It is available for Raspberry Pi 2/3 only; Pi Zero is not supported.
"""

import logging
import subprocess
import sys

import aiy.assistant.auth_helpers
import aiy.audio
import aiy.voicehat
from google.assistant.library import Assistant
from google.assistant.library.event import EventType

import homeassistant.remote as remote
import my_config

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)


def home_assistant(type, entity, state):
    """Send home assistant commands"""
    logging.info("Home Assistant Command received: " + type + " " +
                   entity + " " + state)
    try:
        api = remote.API(my_config.home_assistant_address, my_config.home_assistant_password)
        if type == 'get_state':
            response = remote.get_state(api, entity)
            logging.info(response)
            reply = response.attributes['friendly_name'] + " is " + response.state
            print(response)
            if 'unit_of_measurement' in response.attributes:
                reply = reply + " " + response.attributes['unit_of_measurement']
            aiy.audio.say(reply)
        elif type == 'set_state':
            remote.set_state(api, entity, new_state=state)
        elif type == 'notify':
            data = {"title":"Message from home assistant", "message":state}
            remote.call_service(api, 'notify', my_config.home_assistant_notify_platform, data )
    except Exception as e:
            logging.error("Home Assistant error: " + traceback.format_exc())
            aiy.audio.say("Error sending Home Assistant command")


def outside_temperature():
    home_assistant('get_state', 'sensor.outside_temperature', 'none')


def notify_me(text):
    message = (text.replace('notify', '', 1)).strip()
    home_assistant('notify', 'none', message)


def bedtime():
    home_assistant('set_state', 'automation.bedtime', 'on')


def power_off_pi():
    aiy.audio.say('Good bye!')
    subprocess.call('sudo shutdown now', shell=True)


def reboot_pi():
    aiy.audio.say('See you in a bit!')
    subprocess.call('sudo reboot', shell=True)


def say_ip():
    ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
    aiy.audio.say('My IP address is %s' % ip_address.decode('utf-8'))


def process_event(assistant, event):
    status_ui = aiy.voicehat.get_status_ui()
    if event.type == EventType.ON_START_FINISHED:
        status_ui.status('ready')
        if sys.stdout.isatty():
            print('Say "OK, Google" then speak, or press Ctrl+C to quit...')

    elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
        status_ui.status('listening')

    elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:
        print('You said:', event.args['text'])
        text = event.args['text'].lower()
        if text == 'power off':
            assistant.stop_conversation()
            power_off_pi()
        elif text == 'reboot':
            assistant.stop_conversation()
            reboot_pi()
        elif text == 'ip address':
            assistant.stop_conversation()
            say_ip()
        elif text == 'outside temperature':
            assistant.stop_conversation()
            outside_temperature()
        elif text == 'bedtime':
            assistant.stop_conversation()
            bedtime()
        elif 'notify' in text:
            assistant.stop_conversation()
            notify_me(text)


    elif event.type == EventType.ON_END_OF_UTTERANCE:
        status_ui.status('thinking')

    elif event.type == EventType.ON_CONVERSATION_TURN_FINISHED:
        status_ui.status('ready')

    elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
        sys.exit(1)


def main():
    credentials = aiy.assistant.auth_helpers.get_assistant_credentials()
    with Assistant(credentials) as assistant:
        for event in assistant.start():
            process_event(assistant, event)


if __name__ == '__main__':
    main()
