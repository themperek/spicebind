#ifndef ANALOG_DIGITAL_INTERFACE_H
#define ANALOG_DIGITAL_INTERFACE_H

#include "vpi_user.h"
#include "SpiceVpiConfig.h"
#include <string>
#include <unordered_map>
#include <vector>
#include <mutex>
#include <atomic>

namespace spice_vpi {

/**
 * @brief Manages the interface between analog (SPICE) and digital (HDL) signals
 * 
 * This class handles:
 * - Port discovery and management
 * - Signal conversion between analog voltages and digital logic levels
 * - Thread-safe access to port data
 * - Synchronization between SPICE and HDL simulators
 */
class AnalogDigitalInterface {
private:
    struct PortInfo {
        std::string name;          // Full name (e.g., "clk" or "data[0]")
        std::string base_name;     // Base name for vectors (e.g., "data")
        vpiHandle handle;          // VPI handle
        int direction;             // vpiInput or vpiOutput
        int net_type;              // vpiNet, vpiReg, vpiRealVar
        int size;                  // Port size (1 for scalar, >1 for vector)
        bool is_vector;            // True if vector port
        int bit_index;             // Bit index for vector elements (-1 for scalar)
        std::atomic<double> value; // Current value
        std::atomic<bool> changed; // Change flag

        PortInfo();
        PortInfo(const PortInfo &other);
        PortInfo &operator=(const PortInfo &other);
        PortInfo(PortInfo &&other) noexcept;
        PortInfo &operator=(PortInfo &&other) noexcept;
    };

    // Separate storage for inputs and outputs for faster access
    std::unordered_map<std::string, PortInfo> analog_inputs_;  // Digital -> Analog (digital drives analog)
    std::unordered_map<std::string, PortInfo> analog_outputs_; // Analog -> Digital (analog drives digital)

    // Thread safety
    mutable std::mutex inputs_mutex_;
    mutable std::mutex outputs_mutex_;

    // Configuration reference
    const Config::Settings* config_;

    // Utility functions
    double digital_to_analog(int digital_value) const;
    int analog_to_digital(double analog_value) const;
    static std::string create_indexed_name(const std::string &base_name, int index) ;

public:
    /**
     * @brief Constructor
     * @param config Configuration settings to use for signal conversion
     */
    explicit AnalogDigitalInterface(const Config::Settings& config);

    /**
     * @brief Add a port to be managed by this interface
     * @param port VPI handle to the port
     */
    void add_port(vpiHandle port);

    /**
     * @brief Set analog input value (from digital side)
     * @param name Port name
     * @param value Pointer to receive the analog value
     */
    void set_analog_input(const std::string &name, double *value);

    /**
     * @brief Update analog output values from SPICE
     */
    void analog_outputs_update();

    /**
     * @brief Set digital output values (to digital side)
     */
    void set_digital_output();

    /**
     * @brief Update when digital input changes (called from VPI callback)
     * @param handle VPI handle to the changed signal
     */
    void digital_input_update(vpiHandle handle);

    /**
     * @brief Get all analog input names (for SPICE iteration)
     * @return Vector of port names
     */
    std::vector<std::string> get_analog_input_names() const;

    /**
     * @brief Print debug status information
     */
    void print_status() const;
};

} // namespace spice_vpi

#endif // ANALOG_DIGITAL_INTERFACE_H 