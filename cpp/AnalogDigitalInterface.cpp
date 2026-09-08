#include "AnalogDigitalInterface.h"
#include "Debug.h"
#include "ngspice/sharedspice.h"
#include <cctype>
#include <cstring>
#include <cmath>
#include <algorithm>
#include <utility>

namespace spice_vpi {

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
    // Verilator is 2-state: packing vpiX into vpiIntVal drops the bit to 0.
    if (always_put_outputs_) {
        return analog_value > 0.5 * config_->vcc_voltage ? vpi1 : vpi0;
    }
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

static vpiHandle distinct_handle(vpiHandle net, vpiHandle other) {
    return (other != nullptr && other != net) ? other : nullptr;
}

static std::string to_lower_copy(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return s;
}

static vpiHandle lookup_by_name(const std::string &name, vpiHandle scope) {
    if (name.empty()) {
        return nullptr;
    }
    return vpi_handle_by_name(const_cast<char *>(name.c_str()), scope);
}

static std::string parent_path(const std::string &instance_name) {
    const auto dot = instance_name.rfind('.');
    if (dot == std::string::npos) {
        return {};
    }
    return instance_name.substr(0, dot);
}

static std::string instance_leaf(const std::string &instance_name) {
    const auto dot = instance_name.rfind('.');
    return dot == std::string::npos ? instance_name : instance_name.substr(dot + 1);
}

static std::string trailing_digits(const std::string &name) {
    size_t i = name.size();
    while (i > 0 && std::isdigit(static_cast<unsigned char>(name[i - 1]))) {
        --i;
    }
    return name.substr(i);
}

// Unique parent/TOP net named like the instance port (`osc` or `dco_osc`).
static vpiHandle scan_scope_alias(vpiHandle scope, vpiHandle net, const std::string &port_name) {
    if (scope == nullptr) {
        return nullptr;
    }
    const std::string port_l = to_lower_copy(port_name);
    const std::string usuffix = "_" + port_l;
    vpiHandle found = nullptr;
    int matches = 0;

    vpiHandle iter = vpi_iterate(vpiReg, scope);
    if (iter == nullptr) {
        return nullptr;
    }
    vpiHandle obj = nullptr;
    while ((obj = vpi_scan(iter)) != nullptr) {
        if (obj == net) {
            continue;
        }
        const char *n = vpi_get_str(vpiName, obj);
        if (n == nullptr) {
            continue;
        }
        const std::string cand = to_lower_copy(n);
        bool match = (cand == port_l);
        if (!match && cand.size() > usuffix.size()
            && cand.compare(cand.size() - usuffix.size(), usuffix.size(), usuffix) == 0) {
            match = true;
        }
        if (!match) {
            continue;
        }
        found = obj;
        ++matches;
    }
    return matches == 1 ? distinct_handle(net, found) : nullptr;
}

static vpiHandle lookup_named_alias(vpiHandle net, const std::string &name, const std::string &parent) {
    if (name.empty()) {
        return nullptr;
    }
    // Prefer the user DUT net (tb.Y0) over the Verilator wrapper (TOP.Y0).
    // Cocotb samples the DUT, not the generated TOP.
    if (!parent.empty()) {
        if (vpiHandle h = distinct_handle(net, lookup_by_name(parent + "." + name, nullptr))) {
            return h;
        }
        if (vpiHandle h = distinct_handle(net, lookup_by_name("TOP." + parent + "." + name, nullptr))) {
            return h;
        }
    }
    if (vpiHandle h = distinct_handle(net, lookup_by_name("TOP." + name, nullptr))) {
        return h;
    }
    return nullptr;
}

// Cocotb on Verilator reads TOP / parent nets, not the nested SpiceBind instance.
static vpiHandle find_top_alias(vpiHandle net, const std::string &port_name, const std::string &instance_name) {
    if (net == nullptr || port_name.empty()) {
        return nullptr;
    }

    const std::string parent = parent_path(instance_name);
    if (vpiHandle h = lookup_named_alias(net, port_name, parent)) {
        return h;
    }

    // tb.inv0.Y is connected as .Y(Y0) — try the instance index as a suffix.
    const std::string digits = trailing_digits(instance_leaf(instance_name));
    if (!digits.empty()) {
        if (vpiHandle h = lookup_named_alias(net, port_name + digits, parent)) {
            return h;
        }
    }

    vpiHandle parent_h = lookup_by_name(parent, nullptr);
    if (parent_h == nullptr && !parent.empty()) {
        parent_h = lookup_by_name("TOP." + parent, nullptr);
    }
    if (vpiHandle h = scan_scope_alias(parent_h, net, port_name)) {
        return h;
    }
    if (vpiHandle h = scan_scope_alias(lookup_by_name("TOP", nullptr), net, port_name)) {
        return h;
    }
    return nullptr;
}

static void put_instance_and_top(vpiHandle inst, vpiHandle top, s_vpi_value *val, PLI_INT32 flags) {
    if (inst != nullptr) {
        vpi_put_value(inst, val, nullptr, flags);
    }
    if (top != nullptr && top != inst) {
        vpi_put_value(top, val, nullptr, flags);
    }
}

vpiHandle AnalogDigitalInterface::add_port(vpiHandle port, const std::string& instance_name) {

    const char *pname_c = vpi_get_str(vpiName, port);
    if (pname_c == nullptr) {
        ERROR("add_port: unnamed object");
        return nullptr;
    }
    std::string pname = pname_c;
    const std::string port_name = pname;

    // Icarus iterates vpiPort (parent + name lookup). Verilator has no vpiPort
    // iterate, so the handle is already the net/reg.
    const int obj_type = vpi_get(vpiType, port);
    vpiHandle module = nullptr;
    vpiHandle net = nullptr;
    if (obj_type == vpiPort) {
        module = vpi_handle(vpiParent, port);
        if (module == nullptr) {
            ERROR("add_port: no parent module for port %s", pname.c_str());
            return nullptr;
        }
        net = vpi_handle_by_name(const_cast<char*>(pname.c_str()), module);
    } else {
        net = port;
        module = vpi_handle(vpiScope, net);
    }

    // Verilator iterate(vpiReg) on the DUT can return the TOP wrapper nets.
    // Cocotb reads instance.port (e.g. flash_adc8.code), so re-resolve there.
    if (!instance_name.empty() && !pname.empty()) {
        const std::string hier = instance_name + "." + pname;
        vpiHandle hier_net = vpi_handle_by_name(const_cast<char*>(hier.c_str()), nullptr);
        if (hier_net != nullptr) {
            net = hier_net;
            module = vpi_handle(vpiScope, net);
        }
    }

    if (net == nullptr) {
        ERROR("add_port: net %s not found", pname.c_str());
        return nullptr;
    }

    vpiHandle top_alias = find_top_alias(net, port_name, instance_name);
    if (top_alias != nullptr) {
        DBG("port %s also drives/reads TOP alias", port_name.c_str());
    }

    std::string module_path;
    if (module != nullptr) {
        const char *mname = vpi_get_str(vpiFullName, module);
        if (mname != nullptr) {
            module_path = mname;
        }
    }
    // Verilator scopes live under the generated TOP wrapper. SPICE names
    // follow HDL_INSTANCE (tb.inv0), not TOP.tb.inv0.
    if (module_path.compare(0, 4, "TOP.") == 0) {
        module_path = module_path.substr(4);
    }

    // If full path discovery is enabled, add the module path to the port name
    if (config_->full_path_discovery) {
        pname = module_path + "." + pname;
    }
    
    // Lowercase the port name — SPICE is case insensitive
    pname = to_lower_copy(std::move(pname));

    int dir = vpi_get(vpiDirection, port);
    int port_size = vpi_get(vpiSize, port);
    int net_type = vpi_get(vpiType, net);

    // Validate net type. Verilator reports many wires as vpiReg; SV bit/logic is 620.
    constexpr int kVpiBitVar = 620;
    if (net_type != vpiNet && net_type != vpiReg && net_type != vpiRealVar && net_type != vpiRegBit
        && net_type != kVpiBitVar) {
        ERROR("add_port: unsupported net type %d for %s", net_type, pname.c_str());
        return nullptr;
    }

    DBG("Adding port: %s, dir=%d, size=%d, net_type=%d", pname.c_str(), dir, port_size, net_type);

    if (port_size > 1) {
        // Vector port - one spice node per bit. Store the parent net so Verilator
        // can take a vpiIntVal put on the whole vector (bit puts do not update the
        // wrapper port that cocotb reads).
        for (int i = 0; i < port_size; i++) {
            std::string indexed_name = create_indexed_name(pname, i);
            PortInfo port_info;
            port_info.name = indexed_name;
            port_info.base_name = pname;
            port_info.handle = net;
            port_info.top_handle = top_alias;
            port_info.direction = dir;
            port_info.net_type = net_type;
            port_info.size = port_size;
            port_info.is_vector = true;
            port_info.bit_index = i;
            port_info.value = 0.0;
            port_info.changed = true;

            std::string spice_name = "v(" + indexed_name + ")";
            if (dir == vpiInput) {
                std::lock_guard<std::mutex> lock(inputs_mutex_);
                analog_inputs_.emplace(indexed_name, std::move(port_info));
                DBG("Added analog input: %s", indexed_name.c_str());
            } else if (dir == vpiOutput) {
                std::lock_guard<std::mutex> lock(outputs_mutex_);
                analog_outputs_.emplace(spice_name, std::move(port_info));
                DBG("Added analog output: %s", indexed_name.c_str());
                if (i == 0) {
                    INFO("analog output %s[%d:0] -> v(%s[i])", pname.c_str(), port_size - 1,
                         pname.c_str());
                }
            }
        }
    } else {
        // Scalar port
        PortInfo port_info;
        port_info.name = pname;
        port_info.base_name = pname;
        port_info.handle = net;
        port_info.top_handle = top_alias;
        port_info.direction = dir;
        port_info.net_type = net_type;
        port_info.size = 1;
        port_info.is_vector = false;
        port_info.bit_index = -1;
        port_info.value = 0.0;
        port_info.changed = true;

        std::string spice_name = "v(" + pname + ")";
        if (dir == vpiInput) {
            std::lock_guard<std::mutex> lock(inputs_mutex_);
            analog_inputs_.emplace(pname, std::move(port_info));
            DBG("Added analog input: %s", pname.c_str());
        } else if (dir == vpiOutput) {
            std::lock_guard<std::mutex> lock(outputs_mutex_);
            analog_outputs_.emplace(spice_name, std::move(port_info));
            DBG("Added analog output: %s", pname.c_str());
            INFO("analog output %s -> %s", pname.c_str(), spice_name.c_str());
        }
    }
    return top_alias;
}

void AnalogDigitalInterface::set_analog_input(const char* name, double *value) {
    std::lock_guard<std::mutex> lock(inputs_mutex_);
    auto it = analog_inputs_.find(name);
    if (it != analog_inputs_.end()) {
        *value = it->second.value;
    } else {
        ERROR("analog input %s not found", name);
    }
}


void AnalogDigitalInterface::analog_outputs_update() {
    std::lock_guard<std::mutex> lock(outputs_mutex_);

    for (auto &[name, port_info] : analog_outputs_) {

        pvector_info vector_info = ngGet_Vec_Info(const_cast<char*>(name.c_str())); // TODO: this can be cashed (no need to call ngspice every time)
        if ((vector_info != nullptr) && vector_info->v_length > 0) {
            double new_value = vector_info->v_realdata[vector_info->v_length - 1];

            if (std::abs(port_info.value - new_value) > config_->min_analog_change_threshold) {
                DBG("Analog output %s updated: %g -> %g", name.c_str(), port_info.value, new_value);
                port_info.value = new_value;
                port_info.changed = true;
            }
        }
    }
}

void AnalogDigitalInterface::set_digital_output() {
    std::lock_guard<std::mutex> lock(outputs_mutex_);

    const bool always_put = always_put_outputs_;

    struct VectorPut {
        vpiHandle handle = nullptr;
        vpiHandle top_handle = nullptr;
        int value = 0;
        bool any_changed = false;
    };
    std::unordered_map<std::string, VectorPut> vectors;

    for (auto &[name, port_info] : analog_outputs_) {
        if (port_info.is_vector && !always_put_outputs_) {
            // Icarus: put each bit as a 4-state scalar. Packing into vpiIntVal
            // drops vpiX and breaks analog buses that pass through mid levels.
            if (!port_info.changed) {
                continue;
            }
            port_info.changed = false;
            s_vpi_value val;
            val.format = vpiScalarVal;
            val.value.scalar = analog_to_digital(port_info.value);
            vpiHandle bit = nullptr;
            if (port_info.handle != nullptr && port_info.bit_index >= 0) {
                bit = vpi_handle_by_index(port_info.handle, port_info.bit_index);
            }
            vpi_put_value(bit != nullptr ? bit : port_info.handle, &val, nullptr, vpiNoDelay);
            DBG("Updated digital vector bit %s = %d", name.c_str(), val.value.scalar);
            continue;
        }

        if (port_info.is_vector) {
            auto &acc = vectors[port_info.base_name];
            acc.handle = port_info.handle;
            acc.top_handle = port_info.top_handle;
            if (analog_to_digital(port_info.value) == vpi1) {
                acc.value |= (1 << port_info.bit_index);
            }
            if (port_info.changed || always_put) {
                acc.any_changed = true;
                port_info.changed = false;
            }
            continue;
        }

        if (!port_info.changed && !always_put) {
            continue;
        }
        port_info.changed = false;
        double analog_value = port_info.value;

        if (port_info.net_type == vpiRealVar) {
            s_vpi_value val;
            val.format = vpiRealVal;
            val.value.real = analog_value;
            put_instance_and_top(port_info.handle, port_info.top_handle, &val, vpiNoDelay);
            DBG("Updated digital real %s = %g", name.c_str(), analog_value);
        } else {
            int digital_value = analog_to_digital(analog_value);

            s_vpi_value val;
            val.format = vpiScalarVal;
            val.value.scalar = digital_value;

            put_instance_and_top(port_info.handle, port_info.top_handle, &val, vpiNoDelay);
            DBG("Updated digital scalar %s = %d", name.c_str(), digital_value);
        }
    }

    for (auto &[base_name, acc] : vectors) {
        if (!acc.any_changed || acc.handle == nullptr) {
            continue;
        }
        s_vpi_value val;
        val.format = vpiIntVal;
        val.value.integer = acc.value;
        put_instance_and_top(acc.handle, acc.top_handle, &val, vpiNoDelay);
        DBG("Updated digital vector %s = %d", base_name.c_str(), acc.value);
    }
}


void AnalogDigitalInterface::update_all_digital_inputs() {
    std::lock_guard<std::mutex> lock(inputs_mutex_);

    // Read each stored bit/scalar handle. Do not rebuild names from vpi_get_str:
    // Verilator reports the parent net name for an indexed bit, not "a[0]".
    for (auto &[name, port_info] : analog_inputs_) {
        vpiHandle handle = port_info.top_handle != nullptr ? port_info.top_handle : port_info.handle;
        if (handle == nullptr) {
            continue;
        }

        if (port_info.net_type == vpiRealVar) {
            s_vpi_value val;
            val.format = vpiRealVal;
            vpi_get_value(handle, &val);

            double old_value = port_info.value;
            if (std::abs(old_value - val.value.real) > config_->min_analog_change_threshold) {
                port_info.value = val.value.real;
                port_info.changed = true;
                DBG("Digital input %s updated: %g -> %g", name.c_str(), old_value, val.value.real);
            }
        } else {
            s_vpi_value val;
            val.format = vpiIntVal;
            vpi_get_value(handle, &val);

            int logic = val.value.integer;
            if (port_info.is_vector && port_info.bit_index >= 0 && vpi_get(vpiSize, handle) > 1) {
                logic = (val.value.integer >> port_info.bit_index) & 1;
            }

            double new_analog_value = digital_to_analog(logic);
            double old_value = port_info.value;
            if (std::abs(old_value - new_analog_value) > config_->min_analog_change_threshold) {
                port_info.value = new_analog_value;
                port_info.changed = true;
                DBG("Digital input %s updated: %g -> %g", name.c_str(), old_value, new_analog_value);
            }
        }
    }
}


void AnalogDigitalInterface::digital_input_update(vpiHandle handle) {
    if (handle == nullptr) {
        return;
    }

    const int size = vpi_get(vpiSize, handle);
    const int net_type = vpi_get(vpiType, handle);

    for (auto &[name, port_info] : analog_inputs_) {
        if (port_info.handle != handle && port_info.top_handle != handle) {
            continue;
        }

        if (port_info.net_type == vpiRealVar || net_type == vpiRealVar) {
            s_vpi_value val;
            val.format = vpiRealVal;
            vpi_get_value(handle, &val);

            double old_value = port_info.value;
            if (std::abs(old_value - val.value.real) > config_->min_analog_change_threshold) {
                port_info.value = val.value.real;
                port_info.changed = true;
                DBG("Digital input %s updated: %g -> %g", name.c_str(), old_value, val.value.real);
            }
            continue;
        }

        s_vpi_value val;
        val.format = vpiIntVal;
        vpi_get_value(handle, &val);

        int logic = val.value.integer;
        if (port_info.is_vector && port_info.bit_index >= 0 && size > 1) {
            logic = (val.value.integer >> port_info.bit_index) & 1;
        }

        double new_analog_value = digital_to_analog(logic);
        double old_value = port_info.value;
        if (std::abs(old_value - new_analog_value) > config_->min_analog_change_threshold) {
            port_info.value = new_analog_value;
            port_info.changed = true;
            DBG("Digital input %s updated: %g -> %g", name.c_str(), old_value, new_analog_value);
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
            DBG("  %s: value=%g, changed=%d, type=%d", name.c_str(), port_info.value, port_info.changed, port_info.net_type);
        }
    }
    {
        std::lock_guard<std::mutex> lock(outputs_mutex_);
        DBG("=== Analog Outputs (Analog->Digital) ===");
        for (const auto &[name, port_info] : analog_outputs_) {
            DBG("  %s: value=%g, changed=%d, type=%d", name.c_str(), port_info.value, port_info.changed, port_info.net_type);
        }
    }
}

} // namespace spice_vpi 