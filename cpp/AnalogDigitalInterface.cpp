#include "AnalogDigitalInterface.h"
#include "Debug.h"
#include "ngspice/sharedspice.h"
#include <cstring>
#include <cmath>
#include <algorithm>

namespace spice_vpi {

// PortInfo constructors and operators
AnalogDigitalInterface::PortInfo::PortInfo() 
    : handle(nullptr), direction(0), net_type(0), size(1), is_vector(false), bit_index(-1), value(0.0), changed(false) {}

AnalogDigitalInterface::PortInfo::PortInfo(const PortInfo &other)
    : name(other.name), base_name(other.base_name), handle(other.handle), direction(other.direction), 
      net_type(other.net_type), size(other.size), is_vector(other.is_vector),
      bit_index(other.bit_index), value(other.value.load()), changed(other.changed.load()) {}

auto AnalogDigitalInterface::PortInfo::operator=(const PortInfo &other) -> AnalogDigitalInterface::PortInfo & {
    if (this != &other) {
        name = other.name;
        base_name = other.base_name;
        handle = other.handle;
        direction = other.direction;
        net_type = other.net_type;
        size = other.size;
        is_vector = other.is_vector;
        bit_index = other.bit_index;
        value.store(other.value.load());
        changed.store(other.changed.load());
    }
    return *this;
}

AnalogDigitalInterface::PortInfo::PortInfo(PortInfo &&other) noexcept
    : name(std::move(other.name)), base_name(std::move(other.base_name)), handle(other.handle), 
      direction(other.direction), net_type(other.net_type), size(other.size),
      is_vector(other.is_vector), bit_index(other.bit_index), value(other.value.load()), changed(other.changed.load()) {}

auto AnalogDigitalInterface::PortInfo::operator=(PortInfo &&other) noexcept -> AnalogDigitalInterface::PortInfo & {
    if (this != &other) {
        name = std::move(other.name);
        base_name = std::move(other.base_name);
        handle = other.handle;
        direction = other.direction;
        net_type = other.net_type;
        size = other.size;
        is_vector = other.is_vector;
        bit_index = other.bit_index;
        value.store(other.value.load());
        changed.store(other.changed.load());
    }
    return *this;
}

// AnalogDigitalInterface implementation
AnalogDigitalInterface::AnalogDigitalInterface(const Config::Settings& config) 
    : config_(&config) {}

auto AnalogDigitalInterface::digital_to_analog(int digital_value) const -> double {
    switch (digital_value) {
    case vpi0:
        return 0.0; // Logic 0
    case vpi1:
        return config_->vcc_voltage; // Logic 1 (configurable VCC)
    default:
        return 0.5 * config_->vcc_voltage; // Unknown -> VCC/2
    }
}

auto AnalogDigitalInterface::analog_to_digital(double analog_value) const -> int {
    if (analog_value < config_->logic_threshold_low) {
        return vpi0; // Logic 0
    } if (analog_value > config_->logic_threshold_high) {
        return vpi1; // Logic 1
    }      
    return vpiX; // Logic X
   
}

std::string AnalogDigitalInterface::create_indexed_name(const std::string &base_name, int index) { 
    return base_name + "[" + std::to_string(index) + "]"; 
}

void AnalogDigitalInterface::add_port(vpiHandle port) {

    std::string pname = vpi_get_str(vpiName, port);

    vpiHandle module = vpi_handle(vpiParent, port);
    if (module == nullptr) {
        ERROR("add_port: no parent module for port %s", pname.c_str());
        return;
    }

    const std::string module_path = vpi_get_str(vpiFullName, module);

    vpiHandle net = vpi_handle_by_name(const_cast<char*>(pname.c_str()), module);
    if (net == nullptr) {
        ERROR("add_port: net %s in module %s not found", pname.c_str(), module_path.c_str());
        return;
    }

    // If full path discovery is enabled, add the module path to the port name
    if (config_->full_path_discovery) {
        pname = module_path + "." + pname;
    }
    
    //Lowercase the port name - spice is case insensitive
    std::transform(pname.begin(), pname.end(), pname.begin(), ::tolower);

    int dir = vpi_get(vpiDirection, port);
    int port_size = vpi_get(vpiSize, port);
    int net_type = vpi_get(vpiType, net);

    // Validate net type
    if (net_type != vpiNet && net_type != vpiReg && net_type != vpiRealVar) {
        ERROR("add_port: unsupported net type %d for %s", net_type, pname.c_str());
        return;
    }

    DBG("Adding port: %s, dir=%d, size=%d, net_type=%d", pname.c_str(), dir, port_size, net_type);

    if (port_size > 1) {
        // Vector port - create entries for each bit
        for (int i = 0; i < port_size; i++) {
            vpiHandle bit_handle = vpi_handle_by_index(net, i);
            if (bit_handle != nullptr) {
                std::string indexed_name = create_indexed_name(pname, i);
                PortInfo port_info;
                port_info.name = indexed_name;
                port_info.base_name = pname;
                port_info.handle = bit_handle;
                port_info.direction = dir;
                port_info.net_type = net_type;
                port_info.size = port_size;
                port_info.is_vector = true;
                port_info.bit_index = i;
                port_info.value.store(0.0);
                port_info.changed.store(true);

                if (dir == vpiInput) {
                    std::lock_guard<std::mutex> lock(inputs_mutex_);
                    analog_inputs_.emplace(indexed_name, std::move(port_info));
                    DBG("Added analog input: %s", indexed_name.c_str());
                } else if (dir == vpiOutput) {
                    std::lock_guard<std::mutex> lock(outputs_mutex_);
                    analog_outputs_.emplace(indexed_name, std::move(port_info));
                    DBG("Added analog output: %s", indexed_name.c_str());
                }
            }
        }
    } else {
        // Scalar port
        PortInfo port_info;
        port_info.name = pname;
        port_info.base_name = pname;
        port_info.handle = net;
        port_info.direction = dir;
        port_info.net_type = net_type;
        port_info.size = 1;
        port_info.is_vector = false;
        port_info.bit_index = -1;
        port_info.value.store(0.0);
        port_info.changed.store(true);

        if (dir == vpiInput) {
            std::lock_guard<std::mutex> lock(inputs_mutex_);
            analog_inputs_.emplace(pname, std::move(port_info));
            DBG("Added analog input: %s", pname.c_str());
        } else if (dir == vpiOutput) {
            std::lock_guard<std::mutex> lock(outputs_mutex_);
            analog_outputs_.emplace(pname, std::move(port_info));
            DBG("Added analog output: %s", pname.c_str());
        }
    }
}

void AnalogDigitalInterface::set_analog_input(const std::string &name, double *value) {
    std::lock_guard<std::mutex> lock(inputs_mutex_);
    auto it = analog_inputs_.find(name);
    if (it != analog_inputs_.end()) {
        *value = it->second.value.load();
    } else {
        ERROR("analog input %s not found", name.c_str());
    }
}


void AnalogDigitalInterface::analog_outputs_update() {
    std::lock_guard<std::mutex> lock(outputs_mutex_);

    // TODO: this seems slow

    for (auto &[name, port_info] : analog_outputs_) {
        std::string spice_name = "v(" + name + ")";
        std::vector<char> mutable_buffer(spice_name.begin(), spice_name.end());
        mutable_buffer.push_back('\0');

        pvector_info vector_info = ngGet_Vec_Info(mutable_buffer.data());
        if ((vector_info != nullptr) && vector_info->v_length > 0) {
            double new_value = vector_info->v_realdata[vector_info->v_length - 1];
            double old_value = port_info.value.load();

            if (std::abs(old_value - new_value) > config_->min_analog_change_threshold) {
                port_info.value.store(new_value);
                port_info.changed.store(true);
                DBG("Analog output %s updated: %g -> %g", name.c_str(), old_value, new_value);
            }
        }
    }
}

void AnalogDigitalInterface::set_digital_output() {
    std::lock_guard<std::mutex> lock(outputs_mutex_);

    for (auto &[name, port_info] : analog_outputs_) {
        if (port_info.changed.exchange(false)) { // Read and clear change flag
            double analog_value = port_info.value.load();
            
            if(port_info.net_type == vpiRealVar) {
                s_vpi_value val;
                val.format = vpiRealVal;
                val.value.real = analog_value;
                vpi_put_value(port_info.handle, &val, nullptr, vpiNoDelay);
                DBG("Updated digital real %s = %g", name.c_str(), analog_value);
            } else {
                int digital_value = analog_to_digital(analog_value);

                s_vpi_value val;
                val.format = vpiScalarVal;
                val.value.scalar = digital_value;

                vpi_put_value(port_info.handle, &val, nullptr, vpiNoDelay);
                DBG("Updated digital scalar %s = %d", name.c_str(), digital_value);
            }
        }
    }
}


void AnalogDigitalInterface::update_all_digital_inputs() {
    std::lock_guard<std::mutex> lock(inputs_mutex_);
    
    // TODO: this can be optimezed

    for (const auto &[name, port_info] : analog_inputs_) {
        // Get the VPI handle for this input
        vpiHandle handle = port_info.handle;
        if (handle != nullptr) {
            digital_input_update(handle);
        }
    }
}


void AnalogDigitalInterface::digital_input_update(vpiHandle handle) {
    std::string name = vpi_get_str(vpiName, handle);
    int size = vpi_get(vpiSize, handle);
    int net_type = vpi_get(vpiType, handle);

    //If full path discovery is enabled, add the module path to the port name
    if (config_->full_path_discovery) {
        name = vpi_get_str(vpiFullName, handle);
    }

    //Lowercase the port name - spice is case insensitive
    std::transform(name.begin(), name.end(), name.begin(), ::tolower);

    // std::lock_guard<std::mutex> lock(inputs_mutex_);

    DBG("Digital input update: %s size=%d net_type=%d", name.c_str(), size, net_type);

    if (net_type == vpiRealVar) {
        auto it = analog_inputs_.find(name);
        if (it != analog_inputs_.end()) {
            s_vpi_value val;
            val.format = vpiRealVal;
            vpi_get_value(handle, &val);

            double old_value = it->second.value.load();
            DBG("Digital X input %s : %g -> %g", name.c_str(), old_value, val.value.real);

            if (std::abs(old_value - val.value.real) > config_->min_analog_change_threshold) {
                it->second.value.store(val.value.real);
                it->second.changed.store(true);
                DBG("Digital input %s updated: %g -> %g", name.c_str(), old_value, val.value.real);
            }
        }
        else {
            ERROR("Digital input %s not found", name.c_str());
        }
    }
    else if (net_type == vpiNetBit) {
        auto it = analog_inputs_.find(name);
        if (it != analog_inputs_.end()) {
            s_vpi_value val;
            val.format = vpiIntVal;
            vpi_get_value(handle, &val);

            double new_value = digital_to_analog(val.value.integer);
            double old_value = it->second.value.load();
            DBG("Digital Z input %s : %g -> %g", name.c_str(), old_value, new_value);

            if (std::abs(old_value - new_value) > config_->min_analog_change_threshold) {
                it->second.value.store(new_value);
                it->second.changed.store(true);
                DBG("Digital input %s updated: %g -> %g", name.c_str(), old_value, new_value);
            }
        }
        else {
            ERROR("Digital input %s not found", name.c_str());
        }
    }
    else {
        for (int i = 0; i < size; i++) {
            vpiHandle bit_handle = vpi_handle_by_index(handle, i);

            if (bit_handle != nullptr) {
                int bit_index = vpi_get(vpiIndex, bit_handle);

                std::string indexed_name = name;
                if (size > 1) {
                    indexed_name = create_indexed_name(name, bit_index);
                }

                auto it = analog_inputs_.find(indexed_name);
                if (it != analog_inputs_.end()) {
                    s_vpi_value bit_val;
                    bit_val.format = vpiIntVal; // Use integer format for individual bits
                    vpi_get_value(bit_handle, &bit_val);

                    double new_analog_value = digital_to_analog(bit_val.value.integer);
                    double old_value = it->second.value.load();
                    DBG("Digital Y input %s : %g -> %g", indexed_name.c_str(), old_value, new_analog_value);

                    if (std::abs(old_value - new_analog_value) > config_->min_analog_change_threshold) {
                        it->second.value.store(new_analog_value);
                        it->second.changed.store(true);
                        DBG("Digital input %s updated: %g -> %g", indexed_name.c_str(), old_value, new_analog_value);
                    }
                }
                else {
                    ERROR("Digital input %s not found", indexed_name.c_str());
                }
            }
            else {
                ERROR("Digital input %s not found", name.c_str());
            }
        }
    }
}

auto AnalogDigitalInterface::get_analog_input_names() const -> std::vector<std::string> {
    std::lock_guard<std::mutex> lock(inputs_mutex_);
    std::vector<std::string> names;
    names.reserve(analog_inputs_.size());
    for (const auto &[name, port_info] : analog_inputs_) {
        names.push_back(name);
    }
    return names;
}

void AnalogDigitalInterface::print_status() const {
    {
        std::lock_guard<std::mutex> lock(inputs_mutex_);
        DBG("=== Analog Inputs (Digital->Analog) ===");
        for (const auto &[name, port_info] : analog_inputs_) {
            DBG("  %s: value=%g, changed=%d, type=%d", name.c_str(), port_info.value.load(), port_info.changed.load(), port_info.net_type);
        }
    }
    {
        std::lock_guard<std::mutex> lock(outputs_mutex_);
        DBG("=== Analog Outputs (Analog->Digital) ===");
        for (const auto &[name, port_info] : analog_outputs_) {
            DBG("  %s: value=%g, changed=%d, type=%d", name.c_str(), port_info.value.load(), port_info.changed.load(), port_info.net_type);
        }
    }
}

} // namespace spice_vpi 