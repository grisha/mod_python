from mod_python import apache

apache.log_error("dummymodule / {0!s}".format(apache.interpreter))

def function():
    apache.log_error("dummymodule::function / {0!s}".format(apache.interpreter))
    apache.main_server.get_options()["dummymodule::function"] = "1"
