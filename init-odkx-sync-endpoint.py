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
from os import fdopen, remove, path
from xml import dom

def run_interactive_config():
    env_file_location = os.path.join(os.path.dirname(__file__), "config", "https.env")

    try:
        env = parse_env_file(env_file_location)
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
    input_domain = input("domain [({})]:".format(env["HTTPS_DOMAIN"]))

    if input_domain != "":
        env["HTTPS_DOMAIN"] = input_domain

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
        enforce_https = input("enforce https [(Y)/n]:").lower().strip()
        if enforce_https == "":
            enforce_https = "y"
            enforce_https = enforce_https[0]
        if enforce_https in ["y", "n"]:
            break

    if enforce_https == "n":
        print("Would you like to run an INSECURE and DANGEROUS server that will share your users's information if exposed to the Internet?")
        insecure = input("run insecure [y/(N)]:").lower().strip()
        if insecure == "":
            insecure = "n"
        if insecure[0] != "y":
            raise RuntimeError("HTTPS is currently required to run a secure public server. Please restart and select to enforce HTTPS")

    enforce_https = enforce_https == "y"

    print("Enforcing https:", enforce_https)
    if enforce_https:
        print("Please provide an admin email for security updates with HTTPS registration")
        input_email = input("admin email [({})]:".format(env["HTTPS_ADMIN_EMAIL"]))

        if input_email != "":
            env["HTTPS_ADMIN_EMAIL"] = input_email

        print("The system will now attempt to setup an HTTPS certificate for this server.")
        print("For this to work you must have already have purchased/acquired a domain name (or subdomain) and setup a DNS A or AAAA record to point at this server's IP address.")
        print("If you have not done this yet, please do it now...")
        time.sleep(1)
        proceed = input("Domain is ready to proceed with certificate acquisition? [(Y)/n]").strip().lower()
        if proceed == "":
            proceed = "y"
        if proceed[0] != "y":
            print("Re-run this script once the domain is ready!")
            exit(1)

        print("Do you wish to supply your own SSL certificate? If not, the script will use certbot (please make sure it is already installed).")
        manual_certificate = input(["y/(N)"]).strip().lower()

        if manual_certificate == "" :
            manual_certificate = "n"
        if manual_certificate[0] != "y":
            os.system("sudo certbot certonly --standalone \
            --email {} \
            -d {} \
            --rsa-key-size 4096 \
            --agree-tos \
            --cert-name bootstrap \
            --keep-until-expiring \
            --non-interactive".format(env["HTTPS_ADMIN_EMAIL"], env["HTTPS_DOMAIN"]))
        else:
            cert_fullchain_path = env.get("CERT_FULLCHAIN_PATH")
            cert_privkey_path = env.get("CERT_PRIVKEY_PATH")
            print('Please enter path to fullchain .pem/.crt file')
            cert_fullchain_path = input("fullchain file [({})]:".format(cert_fullchain_path)).strip() or cert_fullchain_path
            print('Please enter path to private key .pem file')
            cert_privkey_path = input("private key file [({})]:".format(cert_privkey_path)).strip() or cert_privkey_path
            if not cert_fullchain_path or not cert_privkey_path:
                print('Input not provided, re-run this script with correct inputs.')
                exit(1)
            # Compute absolute paths from relative path inputs
            cert_fullchain_path = path.abspath(cert_fullchain_path)
            cert_privkey_path = path.abspath(cert_privkey_path)
            if not path.exists(cert_fullchain_path) or not path.exists(cert_privkey_path):
                print('File at the given path do not exists, re-run this script with correct inputs.')
                exit(1)
            env['CERT_FULLCHAIN_PATH'] = cert_fullchain_path
            env['CERT_PRIVKEY_PATH'] = cert_privkey_path

        print("Attempting to save updated https configuration")
        write_to_env_file(env_file_location, env)

    return (enforce_https, env)


def replaceInFile(file_path, pattern, subst):
    fh, abs_path = mkstemp()
    with fdopen(fh,'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                new_file.write(re.sub(pattern, subst, line))
    copymode(file_path, abs_path)
    remove(file_path)
    move(abs_path, file_path)


def write_to_env_file(filepath, env: dict):
    """A janky in-memory file write.

    This is not atomic and would use lots of ram for large files.
    """
    with open(filepath, mode="w") as f:
        for (key, val) in env.items():
            f.write("{}={}\n".format(key, val))


def parse_env_file(filepath):
    env = {}
    with open(filepath) as f:
        for line in f:
            try:
                key, val = line.split('=')
            except Exception:
                continue
            env[key] = val.strip()
    return env


def run_docker_builds():
    os.system("docker build --pull -t odk/sync-web-ui https://github.com/odk-x/sync-endpoint-web-ui.git")
    os.system("docker build --pull -t odk/db-bootstrap db-bootstrap")
    os.system("docker build --pull -t odk/openldap openldap")
    os.system("docker build --pull -t odk/phpldapadmin phpldapadmin")


def run_sync_endpoint_build():
    os.system("git clone -b circleci-taketwo --single-branch --depth=1 https://github.com/odk-x/sync-endpoint ; \
               cd sync-endpoint ; \
               mvn -pl org.opendatakit:sync-endpoint-war,org.opendatakit:sync-endpoint-docker-swarm,org.opendatakit:sync-endpoint-common-dependencies clean install -DskipTests")


def deploy_stack(use_https, env):
    if use_https:
        is_certbot = 'CERT_FULLCHAIN_PATH' not in env
        config = 'docker-compose-https-certbot.yml' if is_certbot else 'docker-compose-https.yml'
        envstring = ""
        if not is_certbot:
            envstring = "env CERT_FULLCHAIN_PATH={} CERT_PRIVKEY_PATH={}".format(env["CERT_FULLCHAIN_PATH"], env["CERT_PRIVKEY_PATH"])
        os.system("{} docker stack deploy -c docker-compose.yml -c {} syncldap".format(envstring, config))
    else:
        os.system("docker stack deploy -c docker-compose.yml syncldap")


if __name__ == "__main__":
    https, env = run_interactive_config()
    run_docker_builds()
    run_sync_endpoint_build()
    deploy_stack(https, env)
