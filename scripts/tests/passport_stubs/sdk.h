#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <map>
#include <string>
#include <vector>
#include <openssl/evp.h>
#include <openssl/ecdsa.h>
#include <openssl/x509.h>

#define CONFIG_MIA_PASSPORT_OTA_URL "http://43.143.230.174:8002/xiaozhi/ota/"
#define CONFIG_MIA_PASSPORT_RELEASE_SEQUENCE 1
using esp_err_t = int;
constexpr int ESP_OK=0, ESP_FAIL=-1;
#define ESP_LOGE(...) ((void)0)
#define ESP_LOGI(...) ((void)0)
#define ESP_ERROR_CHECK(x) do { if ((x)!=ESP_OK) std::abort(); } while(0)
using nvs_handle_t = unsigned;
constexpr int NVS_READWRITE=1;
inline std::map<std::string,uint32_t> nv;
inline std::map<std::string,std::string> ns;
inline int nvs_open(const char*,int,nvs_handle_t* h) { *h=1; return 0; }
inline void nvs_close(nvs_handle_t) {}
inline int nvs_commit(nvs_handle_t) { return 0; }
inline int nvs_get_u32(nvs_handle_t,const char* k,uint32_t* v) { if(!nv.contains(k))return -1; *v=nv[k]; return 0; }
inline int nvs_set_u32(nvs_handle_t,const char* k,uint32_t v) { nv[k]=v; return 0; }
inline int nvs_set_str(nvs_handle_t,const char* k,const char* v) { ns[k]=v; return 0; }
inline int nvs_get_str(nvs_handle_t,const char* k,char* v,size_t* n) { if(!ns.contains(k)||ns[k].size()+1>*n)return -1; std::memcpy(v,ns[k].c_str(),ns[k].size()+1); return 0; }

#pragma pack(push,1)
struct esp_image_header_t { uint8_t magic,count,mode,spi; uint32_t entry; uint8_t pins[4]; uint16_t chip_id; uint8_t rest[10]; };
struct esp_image_segment_header_t { uint32_t load,size; };
struct esp_app_desc_t { uint32_t magic_word,secure; uint8_t reserved[8]; char version[32],project_name[32]; uint8_t rest[176]; };
#pragma pack(pop)
static_assert(sizeof(esp_image_header_t)==24 && sizeof(esp_app_desc_t)==256);
constexpr uint8_t ESP_IMAGE_HEADER_MAGIC=0xe9;
constexpr uint32_t ESP_APP_DESC_MAGIC_WORD=0xabcd5432;
inline esp_app_desc_t current_desc{};
inline const esp_app_desc_t* esp_app_get_description() { return &current_desc; }
struct esp_partition_t { uint32_t address,size; uint8_t subtype; };
constexpr uint8_t ESP_PARTITION_SUBTYPE_APP_OTA_0=0x10,ESP_PARTITION_SUBTYPE_APP_OTA_1=0x11;
inline esp_partition_t running{0x20000,0x300000,0x10},target{0x360000,0x300000,0x11};
enum esp_ota_img_states_t { ESP_OTA_IMG_VALID, ESP_OTA_IMG_PENDING_VERIFY };
inline esp_ota_img_states_t image_state=ESP_OTA_IMG_VALID;
inline bool state_missing=false;
inline const esp_partition_t* esp_ota_get_running_partition() { return &running; }
inline const esp_partition_t* esp_ota_get_next_update_partition(void*) { return &target; }
inline int esp_ota_get_state_partition(const esp_partition_t*,esp_ota_img_states_t* s) { if(state_missing)return -1; *s=image_state; return 0; }
inline unsigned boot=0x20000,begins=0,aborts=0,writes=0,rollbacks=0,restarts=0;
inline bool end_fail=false,boot_fail=false,write_fail=false,corrupt_flash=false;
inline std::vector<uint8_t> flash(0x800000,0xff);
inline int esp_ota_mark_app_valid_cancel_rollback() { state_missing=false; image_state=ESP_OTA_IMG_VALID; return 0; }
inline int esp_ota_mark_app_invalid_rollback_and_reboot() { ++rollbacks; running={0x20000,0x300000,0x10}; image_state=ESP_OTA_IMG_VALID; return 0; }
inline void esp_restart() { ++restarts; }
using esp_ota_handle_t = unsigned;
inline size_t written=0;
inline int esp_ota_begin(const esp_partition_t*,size_t,esp_ota_handle_t* h) { ++begins; *h=1; written=0; return 0; }
inline int esp_ota_abort(esp_ota_handle_t) { ++aborts; return 0; }
inline int esp_ota_write(esp_ota_handle_t,const void* p,size_t n) { if(write_fail)return -1; std::memcpy(flash.data()+target.address+written,p,n); if(corrupt_flash)flash[target.address+written]^=1; written+=n; ++writes; return 0; }
inline int esp_ota_end(esp_ota_handle_t) { return end_fail?-1:0; }
inline int esp_ota_set_boot_partition(const esp_partition_t* p) { if(boot_fail)return -1; boot=p->address; return 0; }
inline void* esp_flash_default_chip=nullptr;
inline int esp_flash_read(void*,void* p,uint32_t addr,size_t n) { if(size_t(addr)+n>flash.size())return -1; std::memcpy(p,flash.data()+addr,n); return 0; }
inline int64_t clock_us=0,clock_step=100;
inline int64_t esp_timer_get_time() { return clock_us+=clock_step; }
struct esp_timer_create_args_t { void(*callback)(void*); const char* name; };
using esp_timer_handle_t=void*;
inline void(*timer_callback)(void*)=nullptr;
inline uint64_t timer_duration=0;
inline int esp_timer_create(const esp_timer_create_args_t* a,void** h) { timer_callback=a->callback; *h=reinterpret_cast<void*>(1); return 0; }
inline int esp_timer_start_once(void*,uint64_t n) { timer_duration=n; return 0; }
inline int esp_timer_stop(void*) { timer_duration=0; return 0; }

inline std::vector<uint8_t> response;
inline size_t position=0,read_failure=SIZE_MAX;
inline int status_code=200;
inline int64_t content_length=-2;
struct esp_http_client_config_t { const char* url; int timeout_ms; bool disable_auto_redirect; int(*crt_bundle_attach)(void*); };
using esp_http_client_handle_t=void*;
inline bool redirects_disabled=false;
inline void* esp_http_client_init(const esp_http_client_config_t* c) { redirects_disabled=c->disable_auto_redirect; position=0; return reinterpret_cast<void*>(1); }
inline int esp_http_client_open(void*,int) { return 0; }
inline int64_t esp_http_client_fetch_headers(void*) { return content_length==-2?int64_t(response.size()):content_length; }
inline int esp_http_client_get_status_code(void*) { return status_code; }
inline int esp_http_client_read(void*,char* p,size_t n) { if(position>=read_failure)return -1; n=std::min({n,size_t(73),response.size()-position}); std::memcpy(p,response.data()+position,n); position+=n; return int(n); }
inline int esp_http_client_close(void*) { return 0; }
inline int esp_http_client_cleanup(void*) { return 0; }
inline int esp_crt_bundle_attach(void*) { return 0; }
inline int battery_level=80;
class Board {
public:
 static Board& GetInstance() { static Board b; return b; }
 bool GetBatteryLevel(int& l,bool& charging,bool& discharging) { l=battery_level;charging=false;discharging=true;return true; }
};

// Host implementation of the PSA boundary. The production crypto_psa.cc is compiled
// unchanged; real signatures/hashes use OpenSSL, while the ESP build uses IDF PSA.
using psa_status_t=int;
using psa_key_id_t=unsigned;
constexpr int PSA_SUCCESS=0,PSA_KEY_ID_NULL=0,PSA_ALG_SHA_256=1,PSA_ECC_FAMILY_SECP_R1=1,PSA_KEY_USAGE_VERIFY_HASH=1;
#define PSA_KEY_TYPE_ECC_PUBLIC_KEY(x) (x)
#define PSA_ALG_ECDSA(x) (x)
struct psa_key_attributes_t { int unused; };
#define PSA_KEY_ATTRIBUTES_INIT {0}
inline void psa_set_key_type(psa_key_attributes_t*,int) {}
inline void psa_set_key_bits(psa_key_attributes_t*,int) {}
inline void psa_set_key_usage_flags(psa_key_attributes_t*,int) {}
inline void psa_set_key_algorithm(psa_key_attributes_t*,int) {}
inline void psa_reset_key_attributes(psa_key_attributes_t*) {}
inline int psa_crypto_init() { return 0; }
inline EVP_PKEY* public_key=nullptr;
inline int psa_import_key(psa_key_attributes_t*,const uint8_t* data,size_t n,unsigned* key) {
 if(n!=65)return -1;
 const uint8_t prefix[]={0x30,0x59,0x30,0x13,0x06,0x07,0x2a,0x86,0x48,0xce,0x3d,0x02,0x01,0x06,0x08,0x2a,0x86,0x48,0xce,0x3d,0x03,0x01,0x07,0x03,0x42,0x00};
 std::vector<uint8_t> der(std::begin(prefix),std::end(prefix)); der.insert(der.end(),data,data+n); const uint8_t* p=der.data();
 public_key=d2i_PUBKEY(nullptr,&p,der.size()); *key=1; return public_key?0:-1;
}
inline void psa_destroy_key(unsigned) { EVP_PKEY_free(public_key); public_key=nullptr; }
inline int psa_hash_compute(int,const uint8_t* p,size_t n,uint8_t* out,size_t cap,size_t* len) { if(cap<32)return -1; unsigned l=0; int ok=EVP_Digest(p,n,out,&l,EVP_sha256(),nullptr); *len=l;return ok==1?0:-1; }
inline int psa_verify_hash(unsigned,int,const uint8_t* hash,size_t hn,const uint8_t* raw,size_t n) {
 if(n!=64)return -1;
 ECDSA_SIG* sig=ECDSA_SIG_new(); ECDSA_SIG_set0(sig,BN_bin2bn(raw,32,nullptr),BN_bin2bn(raw+32,32,nullptr));
 unsigned char* der=nullptr; int dn=i2d_ECDSA_SIG(sig,&der);
 EVP_PKEY_CTX* ctx=EVP_PKEY_CTX_new(public_key,nullptr);
 int ok=EVP_PKEY_verify_init(ctx)==1 && EVP_PKEY_CTX_set_signature_md(ctx,EVP_sha256())==1 && EVP_PKEY_verify(ctx,der,dn,hash,hn)==1;
 EVP_PKEY_CTX_free(ctx); OPENSSL_free(der); ECDSA_SIG_free(sig); return ok?0:-1;
}
struct psa_hash_operation_t { EVP_MD_CTX* ctx; };
#define PSA_HASH_OPERATION_INIT {nullptr}
inline int psa_hash_setup(psa_hash_operation_t* op,int) { op->ctx=EVP_MD_CTX_new();return EVP_DigestInit_ex(op->ctx,EVP_sha256(),nullptr)==1?0:-1; }
inline int psa_hash_update(psa_hash_operation_t* op,const uint8_t* p,size_t n) { return EVP_DigestUpdate(op->ctx,p,n)==1?0:-1; }
inline int psa_hash_finish(psa_hash_operation_t* op,uint8_t* p,size_t cap,size_t* len) { if(cap<32)return -1;unsigned l;int ok=EVP_DigestFinal_ex(op->ctx,p,&l);*len=l;return ok==1?0:-1; }
inline void psa_hash_abort(psa_hash_operation_t* op) { EVP_MD_CTX_free(op->ctx);op->ctx=nullptr; }
