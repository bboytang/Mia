#include "sdk.h"
#include "capsule.h"
#include "backend_policy.h"
#include "signed_update.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iterator>

using namespace mia::passport;
static std::vector<uint8_t> original,layout;
static constexpr auto url="http://43.143.230.174:8002/xiaozhi/otaMag/download/fixture";
static void Reset() {
 response=original; std::fill(flash.begin(),flash.end(),0xff);
 std::copy(layout.begin(),layout.end(),flash.begin()+0x8000);
 nv.clear();ns.clear();state_missing=false;image_state=ESP_OTA_IMG_VALID;
 running={0x20000,0x300000,0x10};target={0x360000,0x300000,0x11};boot=running.address;
 begins=aborts=writes=rollbacks=restarts=0;written=0;position=0;
 end_fail=boot_fail=write_fail=corrupt_flash=false;read_failure=SIZE_MAX;
 status_code=200;content_length=-2;clock_us=0;clock_step=100;battery_level=80;
 current_desc={}; std::strcpy(current_desc.version,"1.0.0");
 timer_duration=0; timer_callback=nullptr;
}
static void Rejected(bool erase=false) {
 assert(!Upgrade(url,{})); assert(boot==0x20000);
 assert(begins==(erase?1u:0u));
 if(erase&&!end_fail&&!boot_fail)assert(aborts==1);
}
int main(int argc,char** argv) {
 assert(argc==3);
 std::ifstream bin(argv[1],std::ios::binary),tab(argv[2],std::ios::binary);
 original.assign(std::istreambuf_iterator<char>(bin),{});
 layout.assign(std::istreambuf_iterator<char>(tab),{});
 assert(original.size()==768);
 Reset(); assert(Upgrade(url,{}));assert(begins==1&&writes>1&&boot==target.address&&redirects_disabled);
 assert(ns["status"]=="trial");
 running=target; image_state=ESP_OTA_IMG_PENDING_VERIFY;
 StartBootGuard();assert(timer_duration==120000000&&timer_callback);
 assert(ConfirmBoot());assert(nv["confirmed"]==2&&ns["status"]=="confirmed"&&timer_duration==0);
 // A late queued timer callback cannot invalidate an already confirmed image.
 timer_callback(nullptr); assert(rollbacks==0);
 Reset();response[192]^=1;Rejected();
 Reset();response[35]^=1;Rejected();
 Reset();response[128]^=1;Rejected();
 Reset();response.assign(512,0xe9);Rejected();
 Reset();assert(!Upgrade("http://other.example/xiaozhi/otaMag/download/fixture",{}));assert(begins==0);
 Reset();assert(!Upgrade("https://43.143.230.174:8002/xiaozhi/otaMag/download/fixture",{}));assert(begins==0);
 Reset();status_code=302;Rejected();
 Reset();content_length=original.size();response.pop_back();Rejected(true);
 Reset();content_length=original.size();response.push_back(0);Rejected(true);
 Reset();read_failure=600;Rejected(true);
 Reset();write_fail=true;Rejected(true);
 Reset();corrupt_flash=true;Rejected(true);
 Reset();end_fail=true;Rejected(true);
 Reset();boot_fail=true;Rejected(true);
 Reset();nv["confirmed"]=2;Rejected();
 Reset();flash[0x8000]^=1;Rejected();
 Reset();flash[0x660000]^=1;Rejected();
 Reset();target.address=running.address;Rejected();
 Reset();target.size=0x100000;Rejected();
 Reset();image_state=ESP_OTA_IMG_PENDING_VERIFY;Rejected();
 Reset();battery_level=10;Rejected();
 Reset();response[256+12]=9;Rejected();
 Reset();response[256+48]='2';Rejected();
 Reset();content_length=-1;Rejected();
 Reset();std::strcpy(current_desc.version,"1.0.2");Rejected();
 Reset();clock_step=20000000;Rejected();
 // A trial boot that fails health restores the old slot and records rollback.
 Reset();assert(Upgrade(url,{}));running=target;image_state=ESP_OTA_IMG_PENDING_VERIFY;
 StartBootGuard();timer_callback(nullptr);assert(rollbacks==1&&restarts==1);
 StartBootGuard();assert(ns["status"]=="rolled_back");
 // A reset in the download never selects the partial image.
 Reset();ns["status"]="downloading";StartBootGuard();assert(ns["status"]=="interrupted"&&boot==0x20000);
 // Power failure after IDF confirms, but before persisting the result.
 Reset();ns["status"]="trial";nv["target_addr"]=running.address;nv["target_seq"]=2;
 StartBootGuard();assert(ns["status"]=="confirmed"&&nv["confirmed"]==2);
 Reset();state_missing=true;assert(NeedsBootConfirmation());Rejected();assert(ConfirmBoot());
 assert(!NeedsBootConfirmation()&&nv["confirmed"]==1&&boot==0x20000);
 // Unsupported/malformed URLs and traversal never reach the HTTP client.
 for(auto bad:{"http://43.143.230.174:8002/xiaozhi/otaMag/download/..",
               "http://43.143.230.174:8002/xiaozhi/otaMag/download/a/b",
               "http://43.143.230.174:8002/xiaozhi/otaMag/download/%2e%2e",
               "http://43.143.230.174:8002/xiaozhi/otaMag/download/x?key=y",
               "http://43.143.230.174:80020/xiaozhi/otaMag/download/x"}) {
  assert(!IsFirmwareEndpoint(bad,CONFIG_MIA_PASSPORT_OTA_URL));
 }
 assert(IsNewerVersion("1.0.10","1.0.2"));assert(!IsNewerVersion("1.0","1.0.0"));
 assert(!IsNewerVersion("1.0.1","1.0.10"));assert(IsNewerVersion("2.0","1.99.99"));
 std::cout<<"32 signed OTA, compatibility, transport, storage and boot fault scenarios passed\n";
}
