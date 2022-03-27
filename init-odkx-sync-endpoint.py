#! /usr/bin/env python3

"""An interactive script to configure ODK-X sync endpoint on first run.

This is a first attempt at a proof of concept script, and has no
support for internationalization.

"""
import time
import os
import re
from tempfile import mkstemp
from shutil import move, copymode
from os import fdopen, remove

def run_interactive_config():
    env_file_location = os.path.join(os.path.dirname(__file__), "config", "https.env")

    try:
        domain, email, stack_name = parse_env_file(env_file_location)
        print("Found configuration at {}".format(env_file_location))
    except OSError:
        print("No default https configuration file found at expected path {}. This prevents automatically renewing certs!".format(env_file_location))
        print("Please check your paths and file permissions, and make sure your config repo is up to date.")
        exit(1)

    print("Welcome to the ODK-X sync endpoint installation!")
    print("This script will guide you through setting up your installation")
    print("We'll need some information from you to get started though...")
    time.sleep(1)
    print("")
    print("Please input the domain name you will use for this installation. A valid domain name is required for HTTPS without distributing custom certificates.")
    input_domain = input("domain [({})]:".format(domain))

    if input_domain != "":
        domain = input_domain

    print("")

    print("Enter the Docker Swarm stack name you'd like to use:")
    input_stack_name = input("Docker Swarm stack [({})]:".format(stack_name))

    if input_stack_name != "":
        stack_name = input_stack_name

    print("")
    use_custom_password = input("Do you want to use a custom LDAP administration password (y/N)?")
    if use_custom_password == "y":
        print("")
        print("Please input the password to use for ldap admin")
        default_ldap_pwd = input("Ldap admin password:")

        if default_ldap_pwd != "":
            replaceInFile("ldap.env", r"^\s*LDAP_ADMIN_PASSWORD=.*$", "LDAP_ADMIN_PASSWORD={}".format(default_ldap_pwd))
            print("Password set to: {}".format(default_ldap_pwd))

    while True:
        print("Would you like to enforce HTTPS? We recommend yes.")
        enforce_https = input("enforce https [(Y)/n]:")
        if enforce_https == "":
            enforce_https = "y"
            enforce_https = enforce_https.lower().strip()[0]
        if enforce_https in ["y", "n"]:
            break

    if enforce_https == "n":
        print("Would you like to run an INSECURE and DANGEROUS server that will share your users's information if exposed to the Internet?")
        insecure = input("run insecure [y/(N)]:")
        if insecure == "":
            insecure = "n"
        if insecure.lower().strip()[0] != "y":
            raise RuntimeError("HTTPS is currently required to run a secure public server. Please restart and select to enforce HTTPS")

    enforce_https = enforce_https == "y"

    print("Enforcing https:", enforce_https)
    if enforce_https:
        print("Please provide an admin email for security updates with HTTPS registration")
        input_email = input("admin email [({})]:".format(email))

        if input_email != "":
            email = input_email

        print("The system will now attempt to setup an HTTPS certificate for this server.")
        print("For this to work you must have already have purchased/acquired a domain name (or subdomain) and setup a DNS A or AAAA record to point at this server's IP address.")
        print("If you have not done this yet, please do it now...")
        time.sleep(1)
        proceed = input("Domain is ready to proceed with certificate acquisition? [(Y)/n]")
        if proceed == "":
            proceed = "y"
        if proceed.strip().lower()[0] != "y":
            print("Re-run this script once the domain is ready!")
            exit(1)

        os.system("sudo certbot certonly --standalone \
          --email {} \
          -d {} \
          --rsa-key-size 4096 \
          --agree-tos \
          --cert-name bootstrap \
          --keep-until-expiring \
          --non-interactive".format(email, domain))

        print("Attempting to save updated https configuration")
        write_to_env_file(env_file_location, domain, email, stack_name)
    return enforce_https


def replaceInFile(file_path, pattern, subst):
    fh, abs_path = mkstemp()
    with fdopen(fh,'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                new_file.write(re.sub(pattern, subst, line))
    copymode(file_path, abs_path)
    remove(file_path)
    move(abs_path, file_path)

def write_to_env_file(filepath, domain_name, email, stack_name):
    """A janky in-memory file write.

    This is not atomic and would use lots of ram for large files.
    """
    file_lines = []
    with open(filepath, mode="r") as f:
        for line in f:
            file_lines.append(line)

    with open(filepath, mode="w") as f:
        for line in file_lines:
            if line.startswith("HTTPS_DOMAIN="):
                line = "HTTPS_DOMAIN={}\n".format(domain_name)
            if line.startswith("HTTPS_ADMIN_EMAIL="):
                line = "HTTPS_ADMIN_EMAIL={}\n".format(email)
            if line.startswith("STACK_NAME="):
                line = "STACK_NAME={}\n".format(stack_name)
            f.write(line)


def parse_env_file(filepath):
    domain = None
    email = None
    stack_name = None
    with open(filepath) as f:
        for line in f:
            if line.startswith("HTTPS_DOMAIN="):
                domain=line[13:].strip()
            if line.startswith("HTTPS_ADMIN_EMAIL="):
                email=line[18:].strip()
            if line.startswith("STACK_NAME="):
                stack_name=line[11:].strip()
    return (domain,email,stack_name)


def run_docker_builds():
    os.system("docker build --pull -t odk/sync-web-ui https://github.com/odk-x/sync-endpoint-web-ui.git")
    os.system("docker build --pull -t odk/db-bootstrap db-bootstrap")
    os.system("docker build --pull -t odk/openldap openldap")
    os.system("docker build --pull -t odk/phpldapadmin phpldapadmin")


def run_sync_endpoint_build():
    os.system("git clone -b master --single-branch --depth=1 https://github.com/odk-x/sync-endpoint ; \
               cd sync-endpoint ; \
               mvn -pl org.opendatakit:sync-endpoint-war,org.opendatakit:sync-endpoint-docker-swarm,org.opendatakit:sync-endpoint-common-dependencies clean install -DskipTests")


def deploy_stack(use_https):
    env_file_location = os.path.join(os.path.dirname(__file__), "config", "https.env")
    domain, email, stack_name = parse_env_file(env_file_location)
    if use_https:
        os.system("docker stack deploy -c docker-compose.yml -c docker-compose-https.yml {}".format(stack_name))
    else:
        os.system("docker stack deploy -c docker-compose.yml {}".format(stack_name))


if __name__ == "__main__":
    https = run_interactive_config()
    run_docker_builds()
    run_sync_endpoint_build()
    deploy_stack(https)