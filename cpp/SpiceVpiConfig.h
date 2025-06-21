#ifndef SPICE_VPI_CONFIG_H
#define SPICE_VPI_CONFIG_H

#include <string>
#include <vector>

namespace spice_vpi {

/**
 * @brief Configuration manager for SPICE-VPI bridge
 * 
 * Handles reading and validating environment variables and configuration
 */
class Config {
public:
    struct Settings {
        std::string spice_netlist_path;
        std::vector<std::string> hdl_instance_names;
        bool full_path_discovery = false;  // indicates if HDL_INSTANCE env var had any comma
        double vcc_voltage = 1.0;
        double logic_threshold_low = 0.3;
        double logic_threshold_high = 0.7;
        double min_analog_change_threshold = 1e-9;
        unsigned long long time_precision = 1e12;
    };

    /**
     * @brief Load configuration from environment variables
     * @return Configuration settings
     * @throws std::runtime_error if required environment variables are missing
     */
    static Settings load_from_environment();

    /**
     * @brief Validate configuration settings
     * @param settings Configuration to validate
     * @throws std::invalid_argument if configuration is invalid
     */
    static void validate(const Settings& settings);

private:
    static std::string get_required_env_var(const char* name);
    static std::string get_optional_env_var(const char* name, const std::string& default_value = "");
    static double get_optional_env_double(const char* name, double default_value);
    
    /**
     * @brief Parse comma-separated instance names from environment variable
     * @param env_value The value from HDL_INSTANCE environment variable
     * @param instance_names Output vector to store parsed instance names
     * @param full_path_discovery Output flag indicating if there was any comma
     */
    static void parse_instance_names(const std::string& env_value, 
                                   std::vector<std::string>& instance_names,
                                   bool& full_path_discovery);
};

} // namespace spice_vpi

#endif // SPICE_VPI_CONFIG_H 