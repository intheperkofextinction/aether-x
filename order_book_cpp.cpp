#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <vector>
#include <algorithm>

namespace py = pybind11;

constexpr int MAX_DEPTH = 10;

// Low-latency LOB Mutation in C++
void update_limit_order_book_cpp(
    py::array_t<double>& bids_array,
    py::array_t<double>& asks_array,
    double price,
    int quantity,
    int side,
    int action
) {
    auto bids = bids_array.mutable_unchecked<2>();
    auto asks = asks_array.mutable_unchecked<2>();

    if (side == 0) { // BID SIDE
        if (action == 0) { // Add / Update
            for (int i = 0; i < MAX_DEPTH; ++i) {
                if (bids(i, 0) == price) {
                    bids(i, 1) = static_cast<double>(quantity);
                    return;
                }
                if (bids(i, 0) < price) {
                    // Shift down
                    for (int j = MAX_DEPTH - 1; j > i; --j) {
                        bids(j, 0) = bids(j - 1, 0);
                        bids(j, 1) = bids(j - 1, 1);
                    }
                    bids(i, 0) = price;
                    bids(i, 1) = static_cast<double>(quantity);
                    return;
                }
            }
        } else if (action == 2) { // Delete
            for (int i = 0; i < MAX_DEPTH; ++i) {
                if (bids(i, 0) == price) {
                    for (int j = i; j < MAX_DEPTH - 1; ++j) {
                        bids(j, 0) = bids(j + 1, 0);
                        bids(j, 1) = bids(j + 1, 1);
                    }
                    bids(MAX_DEPTH - 1, 0) = 0.0;
                    bids(MAX_DEPTH - 1, 1) = 0.0;
                    return;
                }
            }
        }
    } else { // ASK SIDE
        if (action == 0) { // Add / Update
            for (int i = 0; i < MAX_DEPTH; ++i) {
                if (asks(i, 0) == price) {
                    asks(i, 1) = static_cast<double>(quantity);
                    return;
                }
                if (asks(i, 0) == 0.0 || asks(i, 0) > price) {
                    // Shift down
                    for (int j = MAX_DEPTH - 1; j > i; --j) {
                        asks(j, 0) = asks(j - 1, 0);
                        asks(j, 1) = asks(j - 1, 1);
                    }
                    asks(i, 0) = price;
                    asks(i, 1) = static_cast<double>(quantity);
                    return;
                }
            }
        } else if (action == 2) { // Delete
            for (int i = 0; i < MAX_DEPTH; ++i) {
                if (asks(i, 0) == price) {
                    for (int j = i; j < MAX_DEPTH - 1; ++j) {
                        asks(j, 0) = asks(j + 1, 0);
                        asks(j, 1) = asks(j + 1, 1);
                    }
                    asks(MAX_DEPTH - 1, 0) = 0.0;
                    asks(MAX_DEPTH - 1, 1) = 0.0;
                    return;
                }
            }
        }
    }
}

PYBIND11_MODULE(aether_cpp_core, m) {
    m.doc() = "C++ Ultra-Low Latency Order Book Engine for Project Aether-X";
    m.def("update_limit_order_book", &update_limit_order_book_cpp, "Mutate LOB levels in native C++");
}
