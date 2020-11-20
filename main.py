from datetime import datetime
from logging import getLogger, StreamHandler, DEBUG, FileHandler, Formatter
from os import mkdir
from os.path import exists
from pathlib import Path
from re import match, IGNORECASE
from shutil import copyfile
from sys import stdout

CREDS_BACKUP_DIR = f"{Path.home()}/.aws/creds_backups"
LOGS_DIR = f"{Path.home()}/.aws/logs"
CREDS_FILE = f"{Path.home()}/.aws/credentials"
CONFIG_FILE = f"{Path.home()}/.aws/config"

DEFAULT_CONFIG = """[default]
region = eu-west-1
output = json
"""
DEFAULT_CONFIG_REGEX = (
    r"(^|\n)\[default\]\nregion\s*=\s*eu-west-1\noutput\s*=\s*(json|yaml)($|\n)"
)

ACCESS_KEY_PATTERN = r"^aws_access_key_id=[A-Z0-9]{20}$"
SECRET_KEY_PATTERN = r"^aws_secret_access_key=[^=]{40}$"
SESSION_TOKEN_PATTERN = r"^aws_session_token=[^=]{892,}$"

try:
    mkdir(CREDS_BACKUP_DIR)
except FileExistsError:
    pass
try:
    mkdir(LOGS_DIR)
except FileExistsError:
    pass

LOGGER = getLogger(__name__)
LOGGER.setLevel(DEBUG)

SH = StreamHandler(stdout)
FH = FileHandler(f"{LOGS_DIR}/{datetime.today().strftime('%Y-%m-%d')}.log")

FORMATTER = Formatter(
    "%(asctime)s\t%(name)s\t[%(levelname)s]\t%(message)s", "%Y-%m-%d %H:%M:%S"
)
FH.setFormatter(FORMATTER)
SH.setFormatter(FORMATTER)
LOGGER.addHandler(FH)
LOGGER.addHandler(SH)


def create_backups():
    """Create backups of the credentials and config file in case anything goes
    wrong
    """

    backup_dttm = datetime.now().strftime("%Y%m%d%H%M%S")

    if exists(CREDS_FILE):
        creds_backup_path = f"{CREDS_BACKUP_DIR}/credentials_{backup_dttm}"
        LOGGER.info("Backing `credentials` up to `%s`", creds_backup_path)

        copyfile(CREDS_FILE, creds_backup_path)
        LOGGER.debug("`credentials` backup complete")

    if exists(CONFIG_FILE):
        config_backup_path = f"{CREDS_BACKUP_DIR}/config_{backup_dttm}"
        LOGGER.info("Backing `config` up to `%s`", config_backup_path)

        copyfile(CONFIG_FILE, config_backup_path)
        LOGGER.debug("`config` backup complete")


def process_config_file():
    """Either create a config file with the default contents, or update the
    existing file if necessary
    """

    if not exists(CONFIG_FILE):
        LOGGER.info("Config file not found, creating default version...")

        with open(CONFIG_FILE, "w") as fin:
            fin.write(DEFAULT_CONFIG)

        LOGGER.debug("Default config file created")
    else:
        with open(CONFIG_FILE) as fin:
            config_contents = fin.read()

        if not bool(match(DEFAULT_CONFIG_REGEX, config_contents, IGNORECASE)):
            LOGGER.info("Config file found, but no default profile")

            config_contents += "\n\n"
            config_contents += DEFAULT_CONFIG

            with open(CONFIG_FILE, "w") as fin:
                fin.write(config_contents)

            LOGGER.info("Default profile added to config file")
        else:
            LOGGER.info("Config found with default profile, no changes made")


def update_creds_file(
    profile_identifier, access_key_string, secret_key_string, session_token_string
):
    """Update the credentials file with new values for the credentials for a
    given profile

    Args:
        profile_identifier (str): the profile which is being updated
        access_key_string (str): new value for the access key
        secret_key_string (str): new value for the secret key
        session_token_string (str): new value for the session token
    """

    with open(CREDS_FILE) as fin:
        creds_contents = fin.read()

    if profile_identifier not in creds_contents:
        LOGGER.info("Profile not found in existing credentials file")

        creds_contents += "\n\n"
        creds_contents += "\n".join(
            [
                profile_identifier,
                access_key_string,
                secret_key_string,
                session_token_string,
            ]
        )

        LOGGER.info("Adding profile to `credentials`")
        with open(CREDS_FILE, "w") as fout:
            fout.write(creds_contents)

    else:
        LOGGER.info("Profile already exists in creds file, will overwrite")

        creds_lines = creds_contents.splitlines()

        for i, line in enumerate(creds_lines):
            if line.strip() == profile_identifier:
                profile_line_num = i
                LOGGER.debug("Profile ID found on line %i", profile_line_num)
                break
        else:
            raise Exception("Unable to find profile identifier in credentials file")

        if match(ACCESS_KEY_PATTERN, creds_lines[profile_line_num + 1], IGNORECASE):
            creds_lines[profile_line_num + 1] = access_key_string
        else:
            raise Exception("Access Key line doesn't match the expected regex")

        if match(SECRET_KEY_PATTERN, creds_lines[profile_line_num + 2], IGNORECASE):
            creds_lines[profile_line_num + 2] = secret_key_string
        else:
            raise Exception("Secret Key line doesn't match the expected regex")

        if match(SESSION_TOKEN_PATTERN, creds_lines[profile_line_num + 3], IGNORECASE):
            creds_lines[profile_line_num + 3] = session_token_string
        else:
            raise Exception("Session Token line doesn't match the expected regex")

        creds_contents = "\n".join(creds_lines)

        LOGGER.info("Updating credentials file with new profile creds")
        with open(CREDS_FILE, "w") as fout:
            fout.write(creds_contents)


def process_credentials():
    """Process the credentials file"""

    profile_identifier, access_key_string, secret_key_string, session_token_string = (
        input(
            "Please use Option 2 in the dialogue box on the SSO sign-on page to copy your credentials, then paste them here without any changes and press enter: \n"
        ),
        input(),
        input(),
        input(),
    )

    if not all(
        [
            bool(
                match(r"^\[[0-9]{12}[A-Z\-_0-9]{6,}\]$", profile_identifier, IGNORECASE)
            ),
            bool(match(ACCESS_KEY_PATTERN, access_key_string)),
            bool(match(SECRET_KEY_PATTERN, secret_key_string)),
            bool(match(SESSION_TOKEN_PATTERN, session_token_string)),
        ]
    ):
        raise Exception("TBD")

    if exists(CREDS_FILE):
        LOGGER.info("`credentials` file already exists, updating as necessary")
        update_creds_file(
            profile_identifier,
            access_key_string,
            secret_key_string,
            session_token_string,
        )
    else:
        creds_content = "\n".join(
            [
                profile_identifier,
                access_key_string,
                secret_key_string,
                session_token_string,
            ]
        )

        with open(CREDS_FILE, "w") as fout:
            fout.write(creds_content)


if __name__ == "__main__":
    create_backups()
    process_config_file()
    process_credentials()
