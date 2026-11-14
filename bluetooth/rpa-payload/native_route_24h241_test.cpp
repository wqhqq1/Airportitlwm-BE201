// Run the 24H241 scan, resolver, routing guards and native filter builders in
// a private mapping. Use a clean local bluetoothd copy and synthetic IRKs.
#include "AuthenticatedRPAPatch.hpp"
#include <CommonCrypto/CommonCrypto.h>
#include <CommonCrypto/CommonDigest.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <sys/mman.h>
#include <vector>

namespace {
constexpr uintptr_t base = 0x100000000;
constexpr size_t pageSize = 4096;
constexpr size_t textSize = 0x9db000;
constexpr size_t mappedSize = 0xa6b000;
constexpr size_t fileSize = 0xa46000;
constexpr uintptr_t payload = 0x1009da380;
constexpr uintptr_t state = 0x100a6af00;
constexpr uintptr_t scan = 0x1001f1a68;
constexpr uintptr_t single = 0x10068b558;
constexpr uintptr_t singleGuard = 0x10068b919;
constexpr std::array<uintptr_t, 2> multiCalls{0x10068b7ba, 0x10068b883};

using Address = std::array<uint8_t, 7>;
using Key = std::array<uint8_t, 16>;
struct Peer { Address address; Key irk; uint8_t valid; };
static_assert(sizeof(Peer) == 24);

std::vector<uint8_t> readFixture(const char *path) {
    std::ifstream stream(path, std::ios::binary);
    assert(stream);
    return {std::istreambuf_iterator<char>(stream), {}};
}

uint32_t bigEndian(const uint8_t *p) {
    return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | p[3];
}

struct Fixture {
    std::vector<uint8_t> bytes;
    size_t offset = 0;
    explicit Fixture(const char *path) : bytes(readFixture(path)) {
        assert(bytes.size() >= 8);
        size_t size = bytes.size();
        if (bigEndian(bytes.data()) == 0xcafebabe) {
            uint32_t count = bigEndian(bytes.data() + 4);
            assert(count <= (bytes.size() - 8) / 20);
            for (uint32_t i = 0; i < count; ++i) {
                auto *arch = bytes.data() + 8 + i * 20;
                if (bigEndian(arch) != 0x01000007) continue;
                offset = bigEndian(arch + 8);
                size = bigEndian(arch + 12);
                break;
            }
            assert(offset > 0 && offset <= bytes.size() && size <= bytes.size() - offset);
        }
        assert(size == 0xa89bb0);
        const uint8_t expected[] = {
            0x25, 0x47, 0xc6, 0x83, 0xe2, 0x06, 0x55, 0x77, 0x81, 0xa7, 0x1e, 0xcb, 0xa0, 0x4d, 0xa1, 0x71,
            0x21, 0xf4, 0x9d, 0x4b, 0xb1, 0x48, 0xca, 0x91, 0xfd, 0xca, 0xf1, 0x90, 0xee, 0x6f, 0xf9, 0xa4
        };
        uint8_t digest[CC_SHA256_DIGEST_LENGTH];
        CC_SHA256(bytes.data() + offset, static_cast<CC_LONG>(size), digest);
        assert(!memcmp(digest, expected, sizeof(digest)) && "expected an unmodified 24H241 x86_64 bluetoothd");
    }
};

struct Tree {
    void *begin = nullptr;
    void *root = nullptr;
    size_t size = 0;
};
struct Node { uint64_t links[4]; uint64_t key; };
struct InsertResult { Node *node; uint64_t inserted; };
struct Observations {
    uint64_t millis = 1000000;
    uint64_t getter = 0;
    std::vector<Address> reports;
    std::vector<uint64_t> keys;
    std::vector<unsigned> stages;
    Node node{};
    void *image = nullptr;
};
Observations observed;
uint64_t canary = 0x123456789abcde00;

Key encrypt(const uint8_t *key, const uint8_t *plain) {
    Key cipher{};
    size_t written = 0;
    assert(CCCrypt(kCCEncrypt, kCCAlgorithmAES, kCCOptionECBMode, key, 16, nullptr,
                   plain, 16, cipher.data(), cipher.size(), &written) == kCCSuccess && written == 16);
    return cipher;
}

uint32_t nativeAES(const uint8_t *key, size_t kn, const uint8_t *plain, size_t pn, uint8_t *out, size_t on) {
    assert(kn == 16 && pn == 16 && on == 16);
    auto cipher = encrypt(key, plain);
    memcpy(out, cipher.data(), cipher.size());
    return 0;
}

uint64_t machTicks() { return observed.millis * 1000000; }
int timebase(uint32_t *info) { info[0] = info[1] = 1; return 0; }
uint64_t zero() { return 0; }
void *retain(void *object) { return object; }
uint64_t peerAddress(void *, void *, unsigned preferRaw) {
    assert(preferRaw == 0);
    return observed.getter;
}
void report(const uint8_t *event, void *) {
    Address address{};
    memcpy(address.data(), event + 1, address.size());
    observed.reports.push_back(address);
}
void logStage(void *dso, void *logger, unsigned kind, const char *fmt, const uint8_t *buf, unsigned n) {
    assert(dso == observed.image && logger == &observed && kind == 0 && n == 12);
    assert(!strcmp(fmt, "%{public}s"));
    uint32_t header;
    const char *message;
    memcpy(&header, buf, sizeof(header));
    memcpy(&message, buf + sizeof(header), sizeof(message));
    assert(header == 0x08220102 && strlen(message) == 16 && !memcmp(message, "BE201RPA stage=", 15));
    assert(message[15] >= '1' && message[15] <= '5');
    observed.stages.push_back(static_cast<unsigned>(message[15] - '0'));
}
void *arrayInsert(Tree *, void *, const uint64_t *key, const uint64_t *value) {
    assert(key == value);
    observed.keys.push_back(*key);
    return nullptr;
}
Node *allocNode(size_t n) {
    assert(n == sizeof(Node));
    observed.node = {};
    return &observed.node;
}
void linkNode(Tree *tree, void *, void **slot, Node *node) {
    assert(slot == &tree->root);
    *slot = node;
    observed.keys.push_back(node->key);
}

enum class Payload { intact, absent, firstWordCorrupt, secondWordCorrupt };

class Scenario {
public:
    Scenario(const Fixture &fixture, Payload mode = Payload::intact) {
        auto *mem = mmap(nullptr, mappedSize + pageSize, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
        assert(mem != MAP_FAILED);
        image = static_cast<uint8_t *>(mem);
        memcpy(image, fixture.bytes.data() + fixture.offset, fileSize);

        unsigned mask = 0;
        for (size_t off = 0; off < textSize; off += pageSize) {
            unsigned role = be201RPAApply(image + off, pageSize, off + fixture.offset);
            if (!role) continue;
            assert((role == 1 || role == 2 || role == 4) && !(mask & role));
            mask |= role;
            assert(be201RPAApply(image + off, pageSize, off + fixture.offset) == (128 | role));
            if (role == 4 && mode == Payload::absent)
                memcpy(image + off, fixture.bytes.data() + fixture.offset + off, pageSize);
        }
        assert(mask == 7);
        if (mode == Payload::firstWordCorrupt) *at(payload) ^= 1;
        if (mode == Payload::secondWordCorrupt) *at(payload + 4) ^= 1;

        // Stand in for system imports and the allocator/sinks. The scan, RPA
        // resolver, AH, OI_Time_Now and filter functions run from the image.
        store(0x1009dc508, &canary);
        store(0x1009dc598, &observed);
        store(0x1009dc0b0, retain);
        store(0x1009dc0a8, zero);
        store(0x100a5ff90, report);
        stub(0x1000d60e9, nativeAES);
        stub(0x1007e5240, machTicks);
        stub(0x1007e5276, timebase);
        stub(0x1007e4ee6, logStage);
        stub(0x1000cbcd3, zero);
        stub(0x10021a3e7, zero);
        stub(0x10068b618, zero);
        stub(0x10067ef8c, peerAddress);
        stub(0x1003049c8, arrayInsert);
        stub(0x1007e4e38, allocNode);
        stub(0x10002c442, linkNode);

        // Keep both original patched CALL instructions at their real image
        // addresses. Provide a standalone ABI-aligned entry/return around each.
        const uint8_t prologue[] = {0x48, 0x83, 0xec, 0x08};  // sub rsp,8
        const uint8_t epilogue[] = {0x48, 0x83, 0xc4, 0x08, 0xc3};  // add rsp,8; ret
        for (auto call : multiCalls) {
            assert(*at(call) == 0xe8);
            memcpy(at(call - sizeof(prologue)), prologue, sizeof(prologue));
            memcpy(at(call + 5), epilogue, sizeof(epilogue));
        }
        assert(mprotect(image, textSize, PROT_READ | PROT_EXEC) == 0);
        assert(mprotect(image + mappedSize, pageSize, PROT_READ | PROT_EXEC) == 0);
    }
    ~Scenario() { assert(munmap(image, mappedSize + pageSize) == 0); }
    Scenario(const Scenario &) = delete;
    Scenario &operator=(const Scenario &) = delete;

    void activate(std::vector<Peer> entries) {
        observed = {};
        observed.image = image;
        peers = std::move(entries);
        store(0x100a601b8, peers.data());
        store(0x100a601c0, static_cast<uint16_t>(peers.size()));
    }

    Address scanReport(const Address &address) {
        uint8_t event[80]{};
        memcpy(event + 1, address.data(), address.size());
        event[0x18] = 0xc9;
        const auto before = observed.reports.size();
        reinterpret_cast<void (*)(uint8_t *)>(at(scan))(event);
        assert(observed.reports.size() == before + 1);
        return observed.reports.back();
    }

    uint64_t filter(uint64_t key) {
        Tree tree;
        observed.getter = key;
        observed.keys.clear();
        reinterpret_cast<Tree *(*)(Tree *, void *, void *)>(at(single))(&tree, this, this);
        assert(observed.keys.size() == 1);
        return observed.keys.front();
    }

    std::vector<uint64_t> arrayFilter(const std::vector<uint64_t> &keys) {
        Tree tree;
        observed.keys.clear();
        reinterpret_cast<void (*)(Tree *, const uint64_t *, size_t, void *)>(at(singleGuard))(
            &tree, keys.data(), keys.size(), nullptr);
        return observed.keys;
    }

    uint64_t multiFilter(uintptr_t call, uint64_t key) {
        Tree tree;
        observed.keys.clear();
        auto insert = reinterpret_cast<InsertResult (*)(Tree *, const uint64_t *, const uint64_t *)>(at(call - 4));
        const auto result = insert(&tree, &key, &key);
        assert(result.node == &observed.node && (result.inserted & 0xff) == 1);
        const auto duplicate = insert(&tree, &key, &key);
        assert(duplicate.node == result.node && (duplicate.inserted & 0xff) == 0);
        assert(observed.keys.size() == 1);
        return observed.keys.front();
    }

    void setBusy(bool busy) { store(state + 8, uint32_t(busy)); }
    void assertUnusedState() { assert(std::all_of(at(state), at(state) + 232, [](uint8_t b) { return !b; })); }
    std::vector<Peer> peers;

private:
    uint8_t *image;
    size_t stubOffset = 0;
    uint8_t *at(uintptr_t vm) { return image + (vm - base); }
    template<typename T> void store(uintptr_t vm, T value) { memcpy(at(vm), &value, sizeof(value)); }

    template<typename T> void stub(uintptr_t vm, T target) {
        // Leave adjacent six-byte import stubs intact.
        uint8_t *trampoline = image + mappedSize + stubOffset;
        uint8_t jump[] = {0x49, 0xbb, 0, 0, 0, 0, 0, 0, 0, 0, 0x41, 0xff, 0xe3};  // movabs r11; jmp r11
        uintptr_t pointer = reinterpret_cast<uintptr_t>(target);
        memcpy(jump + 2, &pointer, sizeof(pointer));
        stubOffset += sizeof(jump);
        assert(stubOffset <= pageSize);
        memcpy(trampoline, jump, sizeof(jump));
        *at(vm) = 0xe9;
        store(vm + 1, static_cast<int32_t>(trampoline - at(vm + 5)));
    }
};

uint64_t number(const Address &address) {
    uint64_t result = 0;
    for (auto b : address) result = (result << 8) | b;
    return result;
}

Address makeRPA(const Peer &peer, uint8_t nonce) {
    Address address{1, 0x41, 0x23, nonce};
    Key key, plain{};
    std::reverse_copy(peer.irk.begin(), peer.irk.end(), key.begin());
    memcpy(plain.data() + 13, address.data() + 1, 3);
    auto cipher = encrypt(key.data(), plain.data());
    memcpy(address.data() + 4, cipher.data() + 13, 3);
    return address;
}

void exercise(Scenario &s, const Peer &a, const Peer &b) {
    s.activate({a, b});
    const auto id = number(a.address);
    const auto raw = makeRPA(a, 1);
    auto unmatched = raw;
    unmatched.back() ^= 1;
    assert(s.scanReport(unmatched) == unmatched && s.scanReport(unmatched) == unmatched);
    assert(s.filter(id) == id);
    assert(s.scanReport(raw) == a.address);
    assert(s.filter(id) == number(raw) && s.filter(number(b.address)) == number(b.address));
    for (auto call : multiCalls) assert(s.multiFilter(call, id) == number(raw));
    assert(s.arrayFilter({}).empty());
    assert(s.arrayFilter(std::vector<uint64_t>(64, id)) == std::vector<uint64_t>(64, number(raw)));
    assert(s.arrayFilter(std::vector<uint64_t>(65, id)) == std::vector<uint64_t>(65, id));

    const auto rotated = makeRPA(a, 2);
    const auto other = makeRPA(b, 3);
    assert(s.scanReport(rotated) == a.address && s.scanReport(other) == b.address);
    const std::vector<uint64_t> expected{number(rotated), number(other), 0, UINT64_MAX};
    assert(s.arrayFilter({id, number(b.address), 0, UINT64_MAX}) == expected);
    observed.millis = 1015000;
    assert(s.filter(id) == number(rotated));
    ++observed.millis;
    assert(s.filter(id) == id);
    observed.millis = 999999;
    assert(s.filter(id) == id);
    observed.millis = 1000000;
    s.setBusy(true);
    assert(s.filter(id) == id);
    s.setBusy(false);
    assert(s.filter(id) == number(rotated));
    const std::vector<unsigned> stages{5, 3, 1, 2, 4};
    assert(observed.stages == stages);
    assert(!memcmp(&s.peers[0], &a, sizeof(a)) && !memcmp(&s.peers[1], &b, sizeof(b)));
}
}  // namespace

int main(int argc, char **argv) {
    assert(argc == 2);
    const Fixture fixture(argv[1]);
    const Peer a{{0, 2, 3, 4, 5, 6, 7}, {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}, 1};
    const Peer b{{0, 3, 4, 5, 6, 7, 8}, {15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0}, 1};
    Scenario first(fixture), second(fixture);
    exercise(first, a, b);
    exercise(second, a, b);
    for (auto mode : {Payload::absent, Payload::firstWordCorrupt, Payload::secondWordCorrupt}) {
        Scenario fallback(fixture, mode);
        fallback.activate({a});
        auto id = number(a.address);
        assert(fallback.scanReport(makeRPA(a, 1)) == a.address);
        assert(fallback.filter(id) == id);
        for (auto call : multiCalls) assert(fallback.multiFilter(call, id) == id);
        assert(observed.stages.empty());
        fallback.assertUnusedState();
    }
    puts("PASS: 24H241 three-page patch and idempotence; real scan/AH/filter code and routing payload at two slides; "
         "both multi call sites, expiry, rollback, lock contention, unmatched RPA, and absent/corrupt payload fallback.");
}
