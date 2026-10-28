#pragma once
// ATSE research extension for the original EdgeDepth C++/ImGui terminal.
// No trading commands, no modification to DOM, footprint, replay, or heatmap.
#include <emscripten/fetch.h>
#include <emscripten/emscripten.h>
#include <imgui.h>
#include <nlohmann/json.hpp>
#include <string>
#include <cstdio>
#include <cmath>
#include <algorithm>

namespace atse {
struct Response {
    nlohmann::json body;
    bool received = false;
    bool pending = false;
    bool valid = false;
    double received_at = 0.0;
    std::string error;
};
struct State {
    Response indicators, advanced, depth;
    bool enabled = true;
    char symbol[25] = "BTC";
    int interval = 1;
    double last_request = -1e6;
    double data_age_limit_ms = 10000.0;
};
inline State& state() { static State s; return s; }
inline const char* intervals[] = {"1m","5m","15m","1h","4h"};
inline const char* root_url = "http://127.0.0.1:8765";
inline double numeric(const nlohmann::json& obj, const char* key, double fallback = NAN) {
    if (!obj.is_object() || !obj.contains(key)) return fallback;
    const auto& v = obj[key];
    if (v.is_number()) return v.get<double>();
    return fallback;
}
inline std::string label(const nlohmann::json& obj, const char* key, const char* fallback = "—") {
    if (!obj.is_object() || !obj.contains(key) || !obj[key].is_string()) return fallback;
    return obj[key].get<std::string>();
}
inline void callback_success(emscripten_fetch_t* fetch) {
    auto* target = static_cast<Response*>(fetch->userData);
    if (!target) { emscripten_fetch_close(fetch); return; }
    target->pending = false;
    target->received = true;
    target->received_at = emscripten_get_now();
    target->valid = false;
    if (fetch->status != 200 || !fetch->data) {
        target->error = "HTTP " + std::to_string(fetch->status);
    } else {
        target->body = nlohmann::json::parse(
            fetch->data, fetch->data + fetch->numBytes, nullptr, false);
        target->valid = target->body.is_object() && !target->body.contains("error");
        target->error = target->valid ? "" : "Malformed JSON or API error";
    }
    emscripten_fetch_close(fetch);
}
inline void callback_error(emscripten_fetch_t* fetch) {
    auto* target = static_cast<Response*>(fetch->userData);
    if (target) {
        target->pending = false;
        target->received = true;
        target->valid = false;
        target->received_at = emscripten_get_now();
        target->error = "Network/API unavailable (HTTP " + std::to_string(fetch->status) + ")";
    }
    emscripten_fetch_close(fetch);
}
inline void request(Response& target, const std::string& path) {
    if (target.pending) return;
    target.pending = true;
    emscripten_fetch_attr_t attrs;
    emscripten_fetch_attr_init(&attrs);
    std::snprintf(attrs.requestMethod, sizeof(attrs.requestMethod), "%s", "GET");
    attrs.attributes = EMSCRIPTEN_FETCH_LOAD_TO_MEMORY;
    attrs.onsuccess = callback_success;
    attrs.onerror = callback_error;
    attrs.userData = &target;
    attrs.timeoutMSecs = 4500;
    emscripten_fetch(&attrs, (std::string(root_url) + path).c_str());
}
inline void refresh() {
    State& s = state();
    // Never issue overlapping requests or mix assets across in-flight snapshots.
    if (s.indicators.pending || s.advanced.pending || s.depth.pending) return;
    std::string sym(s.symbol);
    if (sym.empty() || sym.size() > 24) return;
    for (char c: sym) if (!((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-')) return;
    const std::string q = "?symbol=" + sym + "&interval=" + intervals[s.interval];
    request(s.indicators, "/api/indicators" + q);
    request(s.advanced, "/api/advanced-indicators" + q);
    request(s.depth, "/api/depth?symbol=" + sym);
    s.last_request = emscripten_get_now();
}
inline void maybe_refresh() {
    State& s=state();
    if (s.enabled && emscripten_get_now()-s.last_request >= 8000.0) refresh();
}
inline void print_number(const char* title, double n, const char* suffix = "") {
    if (std::isfinite(n)) ImGui::Text("%s  %.2f%s", title, n, suffix);
    else ImGui::TextDisabled("%s  —", title);
}
inline void response_flag(const char* title, const Response& r) {
    ImGui::TextUnformatted(title);
    ImGui::SameLine();
    if (!r.received) ImGui::TextDisabled("not loaded");
    else if (r.pending) ImGui::TextColored(ImVec4(.89f,.68f,.35f,1), "updating...");
    else if (!r.valid) ImGui::TextColored(ImVec4(1,.38f,.45f,1), "unavailable");
    else ImGui::TextColored(ImVec4(.26f,.82f,.64f,1), "connected");
}
inline void render_panel() {
    State& s = state();
    maybe_refresh();
    if (!s.enabled) return;
    ImGui::SetNextWindowSize(ImVec2(410,550), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowPos(ImVec2(65,100), ImGuiCond_FirstUseEver);
    if (!ImGui::Begin("ATSE | Market Intelligence###atse_native_panel", &s.enabled)) {
        ImGui::End(); return;
    }
    ImGui::TextColored(ImVec4(.25f,.83f,.68f,1), "EDGEDEPTH + ATSE");
    ImGui::SameLine(); ImGui::TextDisabled("Native research extension");
    if (ImGui::InputText("Asset", s.symbol, sizeof(s.symbol),
                         ImGuiInputTextFlags_CharsUppercase | ImGuiInputTextFlags_EnterReturnsTrue))
        s.last_request=-1e6;
    ImGui::SameLine();
    if (ImGui::Combo("Interval", &s.interval, intervals, IM_ARRAYSIZE(intervals)))
        s.last_request=-1e6;
    if (ImGui::Button("Refresh data")) s.last_request=-1e6;
    ImGui::SameLine(); ImGui::TextDisabled("8s polling / read-only");
    ImGui::Separator();
    response_flag("Indicators:",s.indicators);
    response_flag("Advanced:",s.advanced);
    response_flag("Depth:",s.depth);
    ImGui::Separator();
    const auto& i=s.indicators.body;
    if (s.indicators.valid) {
        const auto cci=i.value("cci20",nlohmann::json::object());
        const auto rsi=i.value("rsi14",nlohmann::json::object());
        const auto trend=i.value("ema_trend",nlohmann::json::object());
        print_number("Close:",numeric(i,"close"));
        print_number("CCI(20):",numeric(cci,"value"));
        print_number("RSI(14):",numeric(rsi,"value"));
        print_number("ATR(14):",numeric(i,"atr14"));
        ImGui::Text("EMA trend: %s",label(trend,"direction").c_str());
        const auto bias=label(i,"research_bias","WAIT");
        const ImVec4 col=bias=="LONG"?ImVec4(.25f,.85f,.64f,1):
                         bias=="SHORT"?ImVec4(1,.39f,.47f,1):ImVec4(.95f,.72f,.4f,1);
        ImGui::TextColored(col,"Candle research bias: %s",bias.c_str());
    }
    ImGui::SeparatorText("Hyperliquid execution depth");
    const auto& d=s.depth.body;
    if (s.depth.valid) {
        const auto book=d.value("hyperliquid",nlohmann::json::object());
        const std::string status=label(book,"status","unavailable");
        const double age=numeric(book,"age_ms");
        const bool good=status=="live"&&std::isfinite(age)&&age<=s.data_age_limit_ms;
        ImGui::TextColored(good?ImVec4(.25f,.85f,.64f,1):ImVec4(1,.39f,.47f,1),
                           "Book quality: %s",good?"LIVE":"STALE / UNAVAILABLE");
        print_number("Bid:",numeric(book,"best_bid"));
        print_number("Ask:",numeric(book,"best_ask"));
        print_number("Spread:",numeric(book,"spread_bps")," bps");
        print_number("Near imbalance:",numeric(book,"near_imbalance"));
        print_number("Data age:",age," ms");
        const auto gateway=d.value("gateway",nlohmann::json::object());
        if (gateway.is_object()) {
            const auto books=gateway.value("books",nlohmann::json::object());
            const auto btc=books.is_object()?books.value("BTCUSDT",nlohmann::json::object()):nlohmann::json::object();
            ImGui::TextDisabled("Binance context: %s (not execution depth)",label(btc,"status","offline").c_str());
        }
    }
    ImGui::SeparatorText("Source and signal integrity");
    const bool candle_ready=s.indicators.valid,depth_ready=s.depth.valid &&
        label(s.depth.body.value("hyperliquid",nlohmann::json::object()),"status")=="live" &&
        numeric(s.depth.body.value("hyperliquid",nlohmann::json::object()),"age_ms",1e10)<s.data_age_limit_ms;
    if (!candle_ready || !depth_ready)
        ImGui::TextColored(ImVec4(1,.65f,.37f,1),"DATA GATE: WAIT (missing or stale source)");
    else ImGui::TextColored(ImVec4(.25f,.83f,.65f,1),"DATA GATE: feeds readable (NOT trade confirmation)");
    ImGui::TextWrapped("This panel is independent of the original DOM, footprint, TPO, heatmap and replay. "
        "It does not place orders. Indicator bias alone is not an executable signal.");
    if (!s.indicators.error.empty()) ImGui::TextWrapped("Indicators: %s",s.indicators.error.c_str());
    if (!s.depth.error.empty()) ImGui::TextWrapped("Depth: %s",s.depth.error.c_str());
    ImGui::End();
}
} // namespace atse
