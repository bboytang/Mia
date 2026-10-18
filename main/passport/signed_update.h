#pragma once

#include <cstddef>
#include <functional>
#include <string>

namespace mia::passport {

// Wi-Fi profile only. A capsule is metadata+signature+raw ESP application.
bool Upgrade(const std::string& url, std::function<void(int, size_t)> progress);
void StartBootGuard();
bool IsTrialBoot();
bool NeedsBootConfirmation();
bool ConfirmBoot();
void RollbackBoot();
std::string UpgradeStatusJson();

}  // namespace mia::passport
