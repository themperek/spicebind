#include "Config.h"
#include "Debug.h"
#include <cstdlib>
#include <stdexcept>
#include <sstream>

namespace spice_vpi {

auto Config::load_from_environment() -> Config::Settings {
    Settings settings;
    
    settings.spice_netlist_path = get_required_env_var("SPICE_NETLIST");
    
    // Parse HDL_INSTANCE environment variable
    std::string hdl_instances_str = get_required_env_var("HDL_INSTANCE");
    parse_instance_names(hdl_instances_str, settings.hdl_instance_names, settings.full_path_discovery);
    
    settings.vcc_voltage = get_optional_env_double("VCC", 1.0);
    settings.logic_threshold_low = get_optional_env_double("LOGIC_THRESHOLD_LOW", 0.3 * settings.vcc_voltage);
    settings.logic_threshold_high = get_optional_env_double("LOGIC_THRESHOLD_HIGH", 0.7 * settings.vcc_voltage);
    
    validate(settings);
    return settings;
}

void Config::validate(const Settings& settings) {
    if (settings.spice_netlist_path.empty()) {
        throw std::invalid_argument("SPICE netlist path cannot be empty");
    }
    
    if (settings.hdl_instance_names.empty()) {
        throw std::invalid_argument("HDL instance names cannot be empty");
    }
    
    // Check that all instance names are non-empty
    for (const auto& instance_name : settings.hdl_instance_names) {
        if (instance_name.empty()) {
            throw std::invalid_argument("HDL instance name cannot be empty");
        }
    }
    
    if (settings.vcc_voltage <= 0.0) {
        throw std::invalid_argument("VCC voltage must be positive");
    }
    
    if (settings.logic_threshold_low >= settings.logic_threshold_high) {
        throw std::invalid_argument("Logic threshold low must be less than high");
    }
    
    if (settings.logic_threshold_low < 0.0 || settings.logic_threshold_high > settings.vcc_voltage) {
        throw std::invalid_argument("Logic thresholds must be within [0, VCC] range");
    }
}

auto Config::get_required_env_var(const char* name) -> std::string {
    const char* value = std::getenv(name);
    if (value == nullptr) {
        std::ostringstream oss;
        oss << "Required environment variable '" << name << "' is not set";
        throw std::runtime_error(oss.str());
    }
    return std::string(value);
}

auto Config::get_optional_env_var(const char* name, const std::string& default_value) -> std::string {
    const char* value = std::getenv(name);
    return (value != nullptr) ? std::string(value) : default_value;
}

auto Config::get_optional_env_double(const char* name, double default_value) -> double {
    const char* value = std::getenv(name);
    if (value == nullptr) {
        return default_value;
    }
    
    try {
        return std::stod(value);
    } catch (const std::exception&) {
        std::ostringstream oss;
        oss << "Invalid numeric value for environment variable '" << name << "': " << value;
        throw std::invalid_argument(oss.str());
    }
}

void Config::parse_instance_names(const std::string& env_value, 
                                 std::vector<std::string>& instance_names,
                                 bool& full_path_discovery) {
    instance_names.clear();
    full_path_discovery = false;
    
    if (env_value.empty()) {
        return;
    }
    
    // Check for any comma in the environment variable
    full_path_discovery = (env_value.find(',') != std::string::npos);
    
    std::istringstream stream(env_value);
    std::string instance;
    
    while (std::getline(stream, instance, ',')) {
        // Trim whitespace from the instance name
        size_t start = instance.find_first_not_of(" \t\r\n");
        size_t end = instance.find_last_not_of(" \t\r\n");
        
        if (start != std::string::npos && end != std::string::npos) {
            instance_names.push_back(instance.substr(start, end - start + 1));
        } else if (!instance.empty()) {
            // Handle case where instance might be all whitespace
            instance_names.push_back(instance);
        }
    }
    
    // If there was a trailing comma, the last parsed element might be empty
    if (full_path_discovery && !instance_names.empty() && instance_names.back().empty()) {
        instance_names.pop_back();
    }
}

} // namespace spice_vpi 