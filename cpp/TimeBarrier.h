#ifndef TIME_BARRIER_H
#define TIME_BARRIER_H

#include <mutex>
#include <condition_variable>
#include <array>
#include <atomic>
#include <stdexcept>

namespace spice_vpi {

/**
 * @brief Two-party virtual-time synchronization barrier with shutdown support
 * 
 * Coordinates time progression between two simulation engines (HDL and SPICE).
 * Each engine calls update() with its current time. If one engine gets ahead,
 * it blocks until the other catches up or shutdown is called.
 * 
 * @tparam TimeT Time type (typically unsigned long long for femtosecond precision)
 */
template<typename TimeT>
class TimeBarrier {
public:
    static constexpr int HDL_ENGINE_ID = 0;
    static constexpr int SPICE_ENGINE_ID = 1;

    TimeBarrier() : times_{TimeT{}, TimeT{}}, is_shutdown_(false), needs_redo_(false), next_spice_step_time_(TimeT{}) {}

    /**
     * @brief Update time for one engine and wait for synchronization
     * @param engine_id Engine identifier (HDL_ENGINE_ID or SPICE_ENGINE_ID)
     * @param current_time Current virtual time for this engine
     * @return false if barrier was shut down before sync completed
     */
    bool update(int engine_id, TimeT current_time);

    /**
     * @brief Update time without waiting for synchronization
     * @param engine_id Engine identifier
     * @param current_time Current virtual time for this engine
     */
    void update_no_wait(int engine_id, TimeT current_time);

    /**
     * @brief Get current time for specified engine
     * @param engine_id Engine identifier
     * @return Current time for the engine
     */
    TimeT get_time(int engine_id) const;

    /**
     * @brief Signal shutdown to wake all waiting threads
     */
    void shutdown();

    /**
     * @brief Check if barrier has been shut down
     */
    bool is_shutdown() const;

    // SPICE-specific methods
    void set_needs_redo(bool needs_redo);
    bool needs_redo() const;
    
    void set_next_spice_step_time(TimeT time);
    TimeT get_next_spice_step_time() const;

private:
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::array<TimeT, 2> times_;
    std::atomic<bool> is_shutdown_;
    std::atomic<bool> needs_redo_;
    std::atomic<TimeT> next_spice_step_time_;
    
    void validate_engine_id(int engine_id) const;
};

// Template implementation
template<typename TimeT>
bool TimeBarrier<TimeT>::update(int engine_id, TimeT current_time) {
    validate_engine_id(engine_id);
    
    std::unique_lock<std::mutex> lock(mutex_);
    if (is_shutdown_.load()) {
        return false;
    }

    // Publish our new time
    times_[engine_id] = current_time;
    cv_.notify_all();

    // Wait until the other engine reaches our time or shutdown is called
    const int other_engine = 1 - engine_id;
    cv_.wait(lock, [&] {
        return is_shutdown_.load() || times_[other_engine] >= times_[engine_id];
    });

    return !is_shutdown_.load();
}

template<typename TimeT>
void TimeBarrier<TimeT>::update_no_wait(int engine_id, TimeT current_time) {
    validate_engine_id(engine_id);
    
    std::lock_guard<std::mutex> lock(mutex_);
    times_[engine_id] = current_time;
}

template<typename TimeT>
TimeT TimeBarrier<TimeT>::get_time(int engine_id) const {
    validate_engine_id(engine_id);
    
    std::lock_guard<std::mutex> lock(mutex_);
    return times_[engine_id];
}

template<typename TimeT>
void TimeBarrier<TimeT>::shutdown() {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        is_shutdown_.store(true);
    }
    cv_.notify_all();
}

template<typename TimeT>
bool TimeBarrier<TimeT>::is_shutdown() const {
    return is_shutdown_.load();
}

template<typename TimeT>
void TimeBarrier<TimeT>::set_needs_redo(bool needs_redo) {
    needs_redo_.store(needs_redo);
}

template<typename TimeT>
bool TimeBarrier<TimeT>::needs_redo() const {
    return needs_redo_.load();
}

template<typename TimeT>
void TimeBarrier<TimeT>::set_next_spice_step_time(TimeT time) {
    next_spice_step_time_.store(time);
}

template<typename TimeT>
TimeT TimeBarrier<TimeT>::get_next_spice_step_time() const {
    return next_spice_step_time_.load();
}

template<typename TimeT>
void TimeBarrier<TimeT>::validate_engine_id(int engine_id) const {
    if (engine_id != HDL_ENGINE_ID && engine_id != SPICE_ENGINE_ID) {
        throw std::invalid_argument("Invalid engine ID: must be 0 (HDL) or 1 (SPICE)");
    }
}

} // namespace spice_vpi

#endif // TIME_BARRIER_H 