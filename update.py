import os
import sys
import logging
import requests
import json
from subprocess import Popen, PIPE
from config import TOKEN, PROJECTS

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('output.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

GET = "GET"
POST = "POST"

class Update:

    def __init__(self):
        self.access_token = TOKEN
        self.projects_lookup = PROJECTS
        self.run_update_days_from_now = sys.argv[1]
        self.url = 'https://api.letsfreckle.com/v2/'
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'daily-freckle',
            'X-FreckleToken': self.access_token,
        }
        self.start()

    def get_days_from_now(self):
        return int(self.run_update_days_from_now) - 1

    def get_minutes_from_seconds(self, seconds):
        return int(seconds / 60)

    def get_project_id(self, freckle_name):
        query_params = {
            'name': freckle_name
        }
        projects_url = '{}projects/'.format(self.url)
        response = requests.request(GET, projects_url, params=query_params, headers=self.headers)
        response_json = json.loads(response.content)
        for project in response_json:
            if project['name'] == freckle_name:
                project_id = project['id']
                return project_id

    def make_entry(self, project_id, minutes, date, description):
        make_entry_url = '{}entries/'.format(self.url)
        post_args = {
            'project_id': project_id,
            'minutes': minutes,
            'date': date,
            'description': description,
        }
        return requests.request(POST, make_entry_url, headers=self.headers, data=json.dumps(post_args))

    def get_freckle_name(self, project_name):
        for freckle_name, possible_matches in self.projects_lookup.items():
            if project_name in possible_matches:
                return freckle_name

    def generate_json(self):
        previous_number_days = self.get_days_from_now()
        script = '''
            tell application "Daily"

                set Today to (current date)
                set FromDay to (current date) - ({} * days)

                print json with report "daily overview" from FromDay to Today

            end tell
        '''.format(str(previous_number_days))

        p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        stdout, stderr = p.communicate(script)
        return json.loads(stdout)

    def start(self):
        export_data = self.generate_json()
        for daily_data in export_data:
            date = daily_data['date']
            activities_list = daily_data['activities']
            for activity in activities_list:
                daily_string = activity['activity']
                split_description = daily_string.split(':', 1)
                project_name = split_description[0]
                freckle_name = self.get_freckle_name(project_name)
                if freckle_name != 'Lunch':
                    project_id = self.get_project_id(freckle_name)
                    description =  split_description[1]
                    minutes = self.get_minutes_from_seconds(activity['duration'])
                    response = self.make_entry(project_id, minutes, date, description)
                    if response.status_code == 201:
                        logger.info('Successfully logged - freckle_name={} project_id={} minutes={} date={} description={}'.format(freckle_name, project_id, minutes, date, description))
                    else:
                        logger.warning('Failed to log - status_code={} freckle_name={} project_id={} minutes={} date={} description={}'.format(response.status_code, freckle_name, project_id, minutes, date, description))
    logger.info('Finished!')


if __name__ == '__main__':
    logger.info('Starting to track time')
    Update()
