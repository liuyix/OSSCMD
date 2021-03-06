import logging
from logging import debug, warning, error
import re

class Config(object):
    _instance = None
    _parsed_files = []
    access_id = ""
    secret_access_key = ""
    host_base = "storage.aliyun.com"
    verbosity = logging.WARNING
    list_md5 = False
    human_readable_sizes = False
    force = False
#    get_continue = False
    skip_existing = False
    recursive = False
    acl_public = None
    dry_run = False
    delete_removed = False
    # List of checks to be performed for 'sync'
    sync_checks = ['size', 'md5']
    encoding = "utf-8"
    urlencoding_mode = "normal"

    ## Creating a singleton
    def __new__(self, configfile = None):
        if self._instance is None:
            self._instance = object.__new__(self)
        return self._instance

    def __init__(self, configfile = None):
        if configfile:
            self.read_config_file(configfile)

    def option_list(self):
        retval = []
        for option in dir(self):
            ## Skip attributes that start with underscore or are not string, int or bool
            option_type = type(getattr(Config, option))
            if option.startswith("_") or \
               not (option_type in (
                       type("string"),    # str
                        type(42),    # int
                    type(True))):    # bool
                continue
            retval.append(option)
        return retval

    def read_config_file(self, configfile):
        cp = ConfigParser(configfile)
        for option in self.option_list():
            self.update_option(option, cp.get(option))
        self._parsed_files.append(configfile)

    def dump_config(self, stream):
        ConfigDumper(stream).dump("default", self)

    def update_option(self, option, value):
        if value is None:
            return
        #### Special treatment of some options
        ## verbosity must be known to "logging" module
        if option == "verbosity":
            try:
                setattr(Config, "verbosity", logging._levelNames[value])
            except KeyError:
                error("Config: verbosity level '%s' is not valid" % value)
        ## allow yes/no, true/false, on/off and 1/0 for boolean options
        elif type(getattr(Config, option)) is type(True):    # bool
            if str(value).lower() in ("true", "yes", "on", "1"):
                setattr(Config, option, True)
            elif str(value).lower() in ("false", "no", "off", "0"):
                setattr(Config, option, False)
            else:
                error("Config: value of option '%s' must be Yes or No, not '%s'" % (option, value))
        elif type(getattr(Config, option)) is type(42):        # int
            try:
                setattr(Config, option, int(value))
            except ValueError, e:
                error("Config: value of option '%s' must be an integer, not '%s'" % (option, value))
        else:                            # string
            setattr(Config, option, value)

class ConfigParser(object):
    def __init__(self, file, sections = []):
        self.cfg = {}
        self.parse_file(file, sections)
    
    def parse_file(self, file, sections = []):
        debug("ConfigParser: Reading file '%s'" % file)
        if type(sections) != type([]):
            sections = [sections]
        in_our_section = True
        f = open(file, "r")
        r_comment = re.compile("^\s*#.*")
        r_empty = re.compile("^\s*$")
        r_section = re.compile("^\[([^\]]+)\]")
        r_data = re.compile("^\s*(?P<key>\w+)\s*=\s*(?P<value>.*)")
        r_quotes = re.compile("^\"(.*)\"\s*$")
        for line in f:
            if r_comment.match(line) or r_empty.match(line):
                continue
            is_section = r_section.match(line)
            if is_section:
                section = is_section.groups()[0]
                in_our_section = (section in sections) or (len(sections) == 0)
                continue
            is_data = r_data.match(line)
            if is_data and in_our_section:
                data = is_data.groupdict()
                if r_quotes.match(data["value"]):
                    data["value"] = data["value"][1:-1]
                self.__setitem__(data["key"], data["value"])
                if data["key"] in ("access_key", "secret_key", "gpg_passphrase"):
                    print_value = (data["value"][:2]+"...%d_chars..."+data["value"][-1:]) % (len(data["value"]) - 3)
                else:
                    print_value = data["value"]
                debug("ConfigParser: %s->%s" % (data["key"], print_value))
                continue
            warning("Ignoring invalid line in '%s': %s" % (file, line))

    def __getitem__(self, name):
        return self.cfg[name]
    
    def __setitem__(self, name, value):
        self.cfg[name] = value
    
    def get(self, name, default = None):
        if self.cfg.has_key(name):
            return self.cfg[name]
        return default

class ConfigDumper(object):
    def __init__(self, stream):
        self.stream = stream

    def dump(self, section, config):
        self.stream.write("[%s]\n" % section)
        for option in config.option_list():
            self.stream.write("%s = %s\n" % (option, getattr(config, option)))

