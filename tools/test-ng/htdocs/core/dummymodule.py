from mod_python import apache

apache.log_error("dummymodule / %s" % apache.interpreter)

def function():
    apache.log_error("dummymodule::function / %s" % apache.interpreter)
    apache.main_server.get_options()["dummymodule::function"] = "1"
