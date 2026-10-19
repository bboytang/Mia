#include <cassert>
#include <set>
#include <string>
#include "youmi_ui_model.h"

int main() {
    using namespace youmi_ui;
    std::set<char> entered;
    for (int bank = 0; bank < 11; ++bank)
        for (int cell = 0; cell < 9; ++cell)
            if (const char c = Candidate(bank, cell))
                entered.insert(c);
    assert(entered.size() == 95);
    for (int c = 32; c <= 126; ++c)
        assert(entered.count(char(c)));
    assert(!Candidate(10, 9));
    assert(!ValidPassword("1234567"));
    assert(ValidPassword("Ab9 !@#\"\\"));
    assert(ValidPassword(std::string(63, '~').c_str()));
    assert(!ValidPassword(std::string(64, '~').c_str()));
    assert(ValidPassword(std::string(64, 'a').c_str()));
    assert(!ValidPassword(std::string(65, 'a').c_str()));
    assert(!ValidPassword("1234567\n"));
    char text[5];
    Copy(text, "你你好");
    assert(std::string(text) == "你");
    char smaller[3];
    Copy(smaller, "你好");
    assert(!smaller[0]);
    char ssid[33];
    Copy(ssid, std::string(32, 's').c_str());
    assert(std::strlen(ssid) == 32);
    assert(sizeof(Model) < 2048);
    Model model;
    ApplyMessage(model, "system", "授权码 042617");
    assert(model.page == Page::Info && std::string(model.text).find("042617") != std::string::npos);
    model.page = Page::Success;
    ApplyMessage(model, "system", "在后台点硬件授权\n042617", true);
    assert(model.page == Page::Info);  // Approval remains visible after first provisioning.
    model.page = Page::Settings;
    ApplyMessage(model, "system", "在后台点硬件授权\n042617", true);
    assert(model.page == Page::Info);
    model.page = Page::Face;
    ApplyMessage(model, "user", "你好");
    assert(model.activity == Activity::Thinking);
    model.page = Page::Ota;
    ApplyMessage(model, "system", "68%");
    assert(model.progress == 68 && model.page == Page::Ota);
    ApplyMessage(model, "system", "100%");
    assert(model.progress == 100 && model.page == Page::Ota);  // Downloaded is not installed.
    ApplyMessage(model, "system", "999%");
    assert(model.progress == 100);
    model.page = Page::Connecting;
    Copy(model.ssid, "actual-network");
    Copy(model.password, "private-pass");
    assert(!ApplyConnection(model, false, "actual-network", true));
    assert(model.page == Page::Connecting);
    assert(!ApplyConnection(model, true, "different-network", false));
    assert(model.page == Page::Connecting);
    assert(ApplyConnection(model, true, "actual-network", false));
    assert(model.page == Page::Success && !model.password[0]);
}
