#pragma once
// Native plot overlays, drawn inside the original EdgeDepth ImPlot canvas.
// Levels derive from completed Hyperliquid candles, NOT Binance order book.
#include "ui/atse_research_panel.h"
#include <implot.h>
#include <imgui.h>
#include <cmath>
#include <string>
#include <algorithm>

namespace atse {
inline void draw_price_overlay(const std::string& exchange,const std::string& pair,
                               bool replay, bool compare, double chart_price) {
    State& s=state();
    if (replay || compare || (!s.show_chart_levels && !s.show_chart_hud)) return;
    const std::string sym=normalize_pair(exchange,pair);
    if (sym.empty() || sym!=std::string(s.symbol) || !s.indicators.valid || !s.advanced.valid)
        return; // NEVER overlay BTC research on TAO or any unrelated chart.
    const auto& i=s.indicators.body;
    const auto& a=s.advanced.body;
    const double study_close=numeric(i,"close");
    if (!std::isfinite(chart_price) || chart_price<=0 || !std::isfinite(study_close)
        || study_close<=0 || std::fabs(chart_price/study_close-1)>0.02)
        return; // block mismatched contract units or clearly diverged venues.

    const auto channel=a.value("hilo_channel",nlohmann::json::object());
    const auto ema=i.value("ema_trend",nlohmann::json::object());
    const double high=numeric(channel,"prior_20_high");
    const double low=numeric(channel,"prior_20_low");
    const double ema12=numeric(ema,"ema12");
    const double ema26=numeric(ema,"ema26");
    const double atr=numeric(i,"atr14");
    const ImVec2 origin=ImPlot::GetPlotPos(),size=ImPlot::GetPlotSize();
    if (size.x<120 || size.y<100) return;
    ImDrawList* dl=ImPlot::GetPlotDrawList();
    const auto limits=ImPlot::GetPlotLimits();
    dl->PushClipRect(origin,ImVec2(origin.x+size.x,origin.y+size.y),true);
    if (s.show_chart_levels) {
        struct Level { double p; const char* name; ImU32 color; bool dashed; };
        const Level levels[]={
            {high,"ATSE R20",IM_COL32(244,156,98,230),true},
            {low,"ATSE S20",IM_COL32(62,217,170,230),true},
            {ema12,"EMA12",IM_COL32(88,170,245,190),false},
            {ema26,"EMA26",IM_COL32(180,129,236,190),false},
            {s.show_atr_bands&&std::isfinite(atr)?study_close+atr:NAN,"ATR +1",IM_COL32(126,159,182,170),true},
            {s.show_atr_bands&&std::isfinite(atr)?study_close-atr:NAN,"ATR -1",IM_COL32(126,159,182,170),true}
        };
        for(const Level& level:levels) {
            if (!std::isfinite(level.p)||level.p<=0||
                level.p<limits.Y.Min||level.p>limits.Y.Max) continue;
            const float y=ImPlot::PlotToPixels(limits.X.Min,level.p).y;
            const float x1=origin.x+4,x2=origin.x+size.x-5;
            if (level.dashed) {
                for(float x=x1;x<x2;x+=13.f)
                    dl->AddLine(ImVec2(x,y),ImVec2(std::min(x+7.f,x2),y),level.color,1.4f);
            } else dl->AddLine(ImVec2(x1,y),ImVec2(x2,y),level.color,1.1f);
            const std::string label=std::string(level.name)+"  "+std::to_string((int)std::round(level.p));
            const ImVec2 dim=ImGui::CalcTextSize(label.c_str());
            const float xpos=origin.x+size.x-dim.x-16.f;
            dl->AddRectFilled(ImVec2(xpos-5,y-10),ImVec2(xpos+dim.x+5,y+8),
                              IM_COL32(11,20,30,222),3.0f);
            dl->AddText(ImVec2(xpos,y-8),level.color,label.c_str());
        }
    }
    if (s.show_chart_hud) {
        const auto consensus=a.value("consensus",nlohmann::json::object());
        const std::string bias=label(consensus,"bias","WAIT");
        const ImU32 tone=bias=="LONG"?IM_COL32(49,218,162,255):
                         bias=="SHORT"?IM_COL32(249,99,124,255):
                         IM_COL32(242,191,107,255);
        const ImVec2 top(origin.x+size.x-222,origin.y+12);
        const float bw=209.0f,bh=64.0f;
        dl->AddRectFilled(top,ImVec2(top.x+bw,top.y+bh),IM_COL32(8,18,30,225),7.0f);
        dl->AddRect(top,ImVec2(top.x+bw,top.y+bh),IM_COL32(53,77,97,220),7.0f);
        dl->AddRectFilled(ImVec2(top.x+9,top.y+10),ImVec2(top.x+12,top.y+24),tone,2.f);
        dl->AddText(ImVec2(top.x+20,top.y+9),IM_COL32(148,182,198,255),"ATSE / MODEL CONTEXT");
        dl->AddText(ImVec2(top.x+20,top.y+29),tone,bias.c_str());
        const double rsi=numeric(i.value("rsi14",nlohmann::json::object()),"value");
        char r[90]; std::snprintf(r,sizeof(r),"RSI %.1f  |  CONFIRM ON HL",rsi);
        dl->AddText(ImVec2(top.x+75,top.y+29),IM_COL32(135,160,180,255),r);
        dl->AddText(ImVec2(top.x+20,top.y+46),IM_COL32(104,137,158,255),
                    "Research only / no execution");
    }
    dl->PopClipRect();
}
} // namespace atse
