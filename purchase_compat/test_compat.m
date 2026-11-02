#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include <string.h>

extern BOOL VVInstallCompatibilityForTests(Class storeClass);
static BOOL VVMockInitialized;

@interface VVMockMMKV : NSObject
@property(nonatomic, copy) NSString *mmapID;
@property(nonatomic, strong) NSMutableDictionary<NSString *, NSDate *> *dates;
- (NSDate *)getDateForKey:(NSString *)key;
@end

@implementation VVMockMMKV
+ (void)initialize {
    if (self == objc_getClass("VVMockMMKV")) VVMockInitialized = YES;
}
- (instancetype)init {
    if ((self = [super init])) _dates = [NSMutableDictionary dictionary];
    return self;
}
- (NSDate *)getDateForKey:(NSString *)key {
    return key ? self.dates[key] : nil;
}
@end

static void Check(BOOL condition, NSString *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message.UTF8String);
        exit(1);
    }
    printf("PASS: %s\n", message.UTF8String);
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc == 2 && strcmp(argv[1], "--startup") == 0) {
            Class storeClass = NSClassFromString(@"VVMockMMKV");
            Check(!VVMockInitialized, @"Class lookup leaves storage initialization dormant");
            Check(VVInstallCompatibilityForTests(storeClass), @"Compatibility installs before app startup");
            Check(!VVMockInitialized,
                  @"Installing does not force storage +initialize before app startup");
            Check(VVInstallCompatibilityForTests(storeClass), @"Early repeated installation is harmless");
            Check(!VVMockInitialized, @"Repeated installation still leaves initialization dormant");
            VVMockMMKV *app = [VVMockMMKV new];
            Check(VVMockInitialized, @"The app's first storage use initializes it normally");
            app.mmapID = @"com.johnil.vvebo";
            Check([[app getDateForKey:@"expireDate"]
                        compare:[NSDate dateWithTimeIntervalSince1970:31536000000.0]] == NSOrderedDescending,
                  @"The early-installed hook works after normal initialization");
            Check([app getDateForKey:@"lastSync"] == nil,
                  @"Original fallback works after normal initialization");
            return 0;
        }
        VVMockMMKV *app = [VVMockMMKV new];
        app.mmapID = @"com.johnil.vvebo";
        VVMockMMKV *other = [VVMockMMKV new];
        other.mmapID = @"another.storage";
        NSDate *oldDate = [NSDate dateWithTimeIntervalSince1970:1000];
        NSDate *syncDate = [NSDate dateWithTimeIntervalSince1970:1700000000];
        other.dates[@"expireDate"] = oldDate;
        app.dates[@"lastSync"] = syncDate;

        Check([app getDateForKey:@"expireDate"] == nil,
              @"Baseline: missing local license date reproduces the unavailable state");
        Check(VVInstallCompatibilityForTests(VVMockMMKV.class), @"Compatibility installs");
        NSDate *permanentThreshold = [NSDate dateWithTimeIntervalSince1970:31536000000.0];
        Check([[app getDateForKey:@"expireDate"] compare:permanentThreshold] == NSOrderedDescending,
              @"Missing license reads as valid beyond the app's permanent-license threshold");
        app.dates[@"expireDate"] = oldDate;
        Check([[app getDateForKey:@"expireDate"] compare:permanentThreshold] == NSOrderedDescending,
              @"Expired license reads consistently as locally valid");
        Check(app.dates[@"expireDate"] == oldDate, @"Original stored license data remains unchanged");
        Check([app getDateForKey:@"lastSync"] == syncDate, @"Other date fields remain unchanged");
        Check([other getDateForKey:@"expireDate"] == oldDate,
              @"Other MMKV stores keep their original expiry values");
        Check([app getDateForKey:nil] == nil, @"Nil-key fallback follows the original reader");
        Check(VVInstallCompatibilityForTests(VVMockMMKV.class), @"Installing twice is harmless");
        Check([other getDateForKey:@"expireDate"] == oldDate,
              @"Original fallback still works after repeated installation");
    }
    return 0;
}
