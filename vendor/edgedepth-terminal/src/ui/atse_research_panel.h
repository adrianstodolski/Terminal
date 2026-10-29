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
    std::string requested_symbol;
    int requested_interval = -1;
};
struct State {
    Response indicators, advanced, depth;
    bool enabled = true;
    bool follow_chart = true;
    bool show_chart_levels = true;
    bool show_chart_hud = true;
    bool show_atr_bands = false;
    char symbol[25] = "BTC";
    int interval = 1;
    double last_request = -1e6;
    double data_age_limit_ms = 10000.0;
    double risk_equity = 20000.0;
    double risk_fraction_pct = 0.5;
    double risk_entry = 0.0;
    double risk_stop = 0.0;
    double risk_target = 0.0;
    double risk_leverage = 3.0;
};
inline State& state() { static State s; return s; }
inline const char* intervals[] = {"1m","5m","15m","1h","4h"};
inline const char* root_url = "http://127.0.0.1:8765";
inline std::string normalize_pair(const std::string& exchange, std::string symbol) {
    if (exchange != "binancef" && exchange != "hl") return "";
    for (char& c : symbol) if (c >= 'a' && c <= 'z') c = static_cast<char>(c - 'a' + 'A');
    if (exchange == "binancef") {
        const std::string quote = "USDT";
        if (symbol.size() > quote.size() &&
            symbol.compare(symbol.size()-quote.size(),quote.size(),quote)==0)
            symbol.resize(symbol.size()-quote.size());
    }
    // 1000-unit contracts do not have one-to-one price alignment with HL.
    if (symbol.rfind("1000",0)==0) return "";
    for (char c:symbol) if (!((c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-')) return "";
    return symbol;
}
inline void track_chart(const std::string& exchange,const std::string& pair,int64_t tf_sec) {
    State& s=state();
    if (!s.follow_chart) return;
    const std::string normalized=normalize_pair(exchange,pair);
    if (normalized.empty() || normalized.size()>=sizeof(s.symbol)) return;
    if (normalized != s.symbol) {
        std::snprintf(s.symbol,sizeof(s.symbol),"%s",normalized.c_str());
        // The next poll is blocked while any previous in-flight call exists.
        // Clear old quotes NOW, so another instrument can never display them.
        s.indicators.valid=false;s.advanced.valid=false;s.depth.valid=false;
        s.last_request=-1e6;
    }
    int desired=1;
    if (tf_sec <= 60) desired=0;
    else if(tf_sec <=300) desired=1;
    else if(tf_sec <=900) desired=2;
    else if(tf_sec <=3600) desired=3;
    else desired=4;
    if (desired!=s.interval) {
        s.interval=desired;s.indicators.valid=false;s.advanced.valid=false;
        s.last_request=-1e6;
    }
}
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
    const bool correct_symbol=target->requested_symbol==std::string(state().symbol)
        && target->requested_interval==state().interval;
    if (!correct_symbol) {
        target->error="Stale response discarded";
        emscripten_fetch_close(fetch);
        return;
    }
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
    target.requested_symbol=state().symbol;
    target.requested_interval=state().interval;
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
    // Chart layers keep updating even when the ATSE floating inspector is hidden.
    if (emscripten_get_now()-s.last_request >= 8000.0) refresh();
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
    if (ImGui::IsKeyPressed(ImGuiKey_F8))s.enabled=!s.enabled;
    if (!s.enabled) return;
    ImGui::SetNextWindowSize(ImVec2(380,410), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowPos(ImVec2(280,120), ImGuiCond_FirstUseEver);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding,ImVec2(16,13));
    ImGui::PushStyleVar(ImGuiStyleVar_ItemSpacing,ImVec2(9,8));
    ImGui::PushStyleVar(ImGuiStyleVar_WindowRounding,9.0f);
    ImGui::PushStyleColor(ImGuiCol_WindowBg,ImVec4(.055f,.085f,.125f,.98f));
    ImGui::PushStyleColor(ImGuiCol_Border,ImVec4(.15f,.27f,.33f,1));
    if (!ImGui::Begin("ATSE  /  MARKET INTELLIGENCE###atse_native_panel", &s.enabled)) {
        ImGui::End();ImGui::PopStyleColor(2);ImGui::PopStyleVar(3);return;
    }
    const auto teal=ImVec4(.27f,.88f,.72f,1);
    const auto amber=ImVec4(.97f,.73f,.42f,1);
    const auto red=ImVec4(.99f,.39f,.48f,1);
    ImGui::TextColored(teal,"◈  ATSE / INSTITUTIONAL RESEARCH");
    ImGui::SameLine();ImGui::TextDisabled("  beta");
    ImGui::Separator();
    ImGui::Checkbox("Follow active chart",&s.follow_chart);
    ImGui::SameLine();
    ImGui::TextDisabled("%s / %s",s.symbol,intervals[s.interval]);
    if (!s.follow_chart) {
        if (ImGui::InputText("Symbol",s.symbol,sizeof(s.symbol),ImGuiInputTextFlags_CharsUppercase)) {
            s.indicators.valid=false;s.advanced.valid=false;s.depth.valid=false;s.last_request=-1e6;
        }
        if (ImGui::Combo("Timeframe",&s.interval,intervals,IM_ARRAYSIZE(intervals))) {
            s.indicators.valid=false;s.advanced.valid=false;s.last_request=-1e6;
        }
    }
    if (ImGui::SmallButton("Refresh sources"))s.last_request=-1e6;
    const auto& i=s.indicators.body;
    const auto& adv=s.advanced.body;
    const auto& d=s.depth.body;
    const auto hl=s.depth.valid?d.value("hyperliquid",nlohmann::json::object()):nlohmann::json::object();
    const auto cci=s.indicators.valid?i.value("cci20",nlohmann::json::object()):nlohmann::json::object();
    const auto rsi=s.indicators.valid?i.value("rsi14",nlohmann::json::object()):nlohmann::json::object();
    const auto trend=s.indicators.valid?i.value("ema_trend",nlohmann::json::object()):nlohmann::json::object();
    const auto consensus=s.advanced.valid?adv.value("consensus",nlohmann::json::object()):nlohmann::json::object();
    const auto channel=s.advanced.valid?adv.value("hilo_channel",nlohmann::json::object()):nlohmann::json::object();
    const std::string bias=s.advanced.valid?label(consensus,"bias","WAIT"):"WAIT";
    const double age=numeric(hl,"age_ms");
    const double since=s.depth.received?(emscripten_get_now()-s.depth.received_at):1e10;
    const bool fresh=s.depth.valid&&label(hl,"status")=="live"&&std::isfinite(age)
        &&age+since<s.data_age_limit_ms;
    const bool ready=fresh&&s.indicators.valid&&s.advanced.valid;
    ImGui::TextColored(ready?teal:amber,ready?"●  LIVE / VERIFIED":"●  PARTIAL / STALE DATA");
    ImGui::SameLine(); ImGui::TextDisabled("  %s  |  %s",s.symbol,intervals[s.interval]);
    ImGui::Separator();
    if (ImGui::BeginTabBar("##atse_workspace_tabs",ImGuiTabBarFlags_FittingPolicyScroll)) {
        if (ImGui::BeginTabItem("Market")) {
            ImGui::Spacing();
            if (ImGui::BeginTable("atse_kpi",3,ImGuiTableFlags_SizingStretchSame|ImGuiTableFlags_BordersInnerV)) {
                ImGui::TableNextColumn();ImGui::TextDisabled("RSI / 14");print_number("",numeric(rsi,"value"));
                ImGui::TableNextColumn();ImGui::TextDisabled("CCI / 20");print_number("",numeric(cci,"value"));
                ImGui::TableNextColumn();ImGui::TextDisabled("ATR / 14");print_number("",s.indicators.valid?numeric(i,"atr14"):NAN);
                ImGui::EndTable();
            }
            ImGui::Spacing();
            ImGui::TextDisabled("EMA TREND");ImGui::SameLine();
            ImGui::TextColored(teal,"%s",s.indicators.valid?label(trend,"direction").c_str():"—");
            ImGui::TextDisabled("COMPOSITE");ImGui::SameLine();
            ImGui::TextColored(bias=="LONG"?teal:bias=="SHORT"?red:amber,
                               "%s",ready?bias.c_str():"WAIT");
            ImGui::SeparatorText("MODEL CONFIDENCE");
            ImGui::TextWrapped("A model vote does not represent a probability of profit. "
                               "No live trades are placed.");
            ImGui::EndTabItem();
        }
        if (ImGui::BeginTabItem("Levels")) {
            ImGui::Spacing();
            ImGui::TextDisabled("PRIOR 20-BAR CHANNEL");
            print_number("Resistance",numeric(channel,"prior_20_high"));
            print_number("Support",numeric(channel,"prior_20_low"));
            ImGui::SeparatorText("CHART LAYERS");
            ImGui::Checkbox("Show EMA and channel",&s.show_chart_levels);
            ImGui::Checkbox("Show +/-1 ATR range",&s.show_atr_bands);
            ImGui::Checkbox("Show compact chart HUD",&s.show_chart_hud);
            ImGui::TextDisabled("Research levels are hidden on mismatched venues, "
                                "replay sessions and different contract units.");
            ImGui::EndTabItem();
        }
        if (ImGui::BeginTabItem("Flow")) {
            ImGui::Spacing();
            ImGui::TextDisabled("HYPERLIQUID / EXECUTION VENUE");
            if (fresh) {
                print_number("Best bid",numeric(hl,"best_bid"));
                print_number("Best ask",numeric(hl,"best_ask"));
                print_number("Spread",numeric(hl,"spread_bps")," bps");
                const double imbalance=numeric(hl,"near_imbalance");
                if (std::isfinite(imbalance))
                    ImGui::TextColored(imbalance>=0?teal:red,"Book imbalance %+.3f",imbalance);
                print_number("Freshness",age+since," ms");
            } else ImGui::TextColored(amber,"No usable live execution depth");
            ImGui::TextWrapped("Binance futures book is context only, not a "
                               "substitute for executable Hyperliquid liquidity.");
            ImGui::EndTabItem();
        }
        if (ImGui::BeginTabItem("Risk")) {
            ImGui::TextDisabled("MANUAL POSITION SCENARIO / USDC");
            ImGui::SetNextItemWidth(-1);
            ImGui::InputDouble("Equity (USDC)",&s.risk_equity,0,0,"%.2f");
            ImGui::SetNextItemWidth(-1);
            ImGui::InputDouble("Risk per trade (%)",&s.risk_fraction_pct,0,0,"%.2f");
            ImGui::SetNextItemWidth(-1);
            ImGui::InputDouble("Entry",&s.risk_entry,0,0,"%.4f");
            ImGui::SetNextItemWidth(-1);
            ImGui::InputDouble("Stop",&s.risk_stop,0,0,"%.4f");
            ImGui::SetNextItemWidth(-1);
            ImGui::InputDouble("Target",&s.risk_target,0,0,"%.4f");
            ImGui::SetNextItemWidth(-1);
            ImGui::InputDouble("Leverage cap",&s.risk_leverage,0,0,"%.1f");
            const bool inputs=std::isfinite(s.risk_equity)&&s.risk_equity>0 &&
                std::isfinite(s.risk_fraction_pct)&&s.risk_fraction_pct>0&&s.risk_fraction_pct<=5 &&
                std::isfinite(s.risk_entry)&&s.risk_entry>0 &&
                std::isfinite(s.risk_stop)&&s.risk_stop>0 &&
                std::isfinite(s.risk_target)&&s.risk_target>0 &&
                std::isfinite(s.risk_leverage)&&s.risk_leverage>=1&&s.risk_leverage<=20 &&
                std::fabs(s.risk_entry-s.risk_stop)>1e-9 &&
                ((s.risk_stop<s.risk_entry&&s.risk_target>s.risk_entry)||
                 (s.risk_stop>s.risk_entry&&s.risk_target<s.risk_entry));
            if(inputs){
                const double loss_per_unit=std::fabs(s.risk_entry-s.risk_stop);
                const double budget=s.risk_equity*s.risk_fraction_pct/100.0;
                const double units_by_risk=budget/loss_per_unit;
                const double units_by_leverage=s.risk_equity*s.risk_leverage/s.risk_entry;
                const double units=std::min(units_by_risk,units_by_leverage);
                const double notional=units*s.risk_entry;
                const double loss=units*loss_per_unit;
                const double reward=units*std::fabs(s.risk_target-s.risk_entry);
                ImGui::SeparatorText("SCENARIO");
                ImGui::TextColored(teal,"%s",s.risk_stop<s.risk_entry?"LONG":"SHORT");
                print_number("Max units",units);
                print_number("Notional",notional," USDC");
                print_number("Initial margin est.",notional/s.risk_leverage," USDC");
                print_number("Price-only stop loss",loss," USDC");
                print_number("Potential gain",reward," USDC");
                print_number("Reward / risk",reward/loss);
            } else ImGui::TextColored(amber,"Enter valid entry, stop, target and limits");
            ImGui::TextWrapped("Hypothetical sizing only: excludes trading fees, "
                               "slippage, funding, maintenance margin, liquidation "
                               "distance, cross-collateral and other positions. "
                               "No orders are sent.");
            ImGui::EndTabItem();
        }
        if (ImGui::BeginTabItem("Quality")) {
            ImGui::Spacing();
            response_flag("Indicators",s.indicators);
            response_flag("Advanced",s.advanced);
            response_flag("Hyperliquid",s.depth);
            ImGui::Separator();
            ImGui::TextDisabled("UPDATE INTERVAL   8 SEC");
            ImGui::TextDisabled("MODE              READ ONLY");
            ImGui::TextColored(ready?teal:amber,ready?"DATA GATE: PASS":"DATA GATE: WAIT");
            if (!s.indicators.error.empty())ImGui::TextWrapped("Indicators: %s",s.indicators.error.c_str());
            if (!s.advanced.error.empty())ImGui::TextWrapped("Advanced: %s",s.advanced.error.c_str());
            if (!s.depth.error.empty())ImGui::TextWrapped("Depth: %s",s.depth.error.c_str());
            ImGui::EndTabItem();
        }
        ImGui::EndTabBar();
    }
    ImGui::Separator();
    ImGui::TextDisabled("ATSE TITAN  /  Native Research  /  F8 to toggle");
    ImGui::End();ImGui::PopStyleColor(2);ImGui::PopStyleVar(3);
}
} // namespace atse
