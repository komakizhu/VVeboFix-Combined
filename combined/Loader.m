#import <Foundation/Foundation.h>

extern void VVInstallNetworkCompatibility(void);
extern BOOL VVInstallPurchaseCompatibility(Class storeClass);

#if !VV_COMPAT_TESTING
__attribute__((constructor))
static void VVLoadCombinedFix(void) {
    @autoreleasepool {
        NSBundle *bundle = NSBundle.mainBundle;
        if (![bundle.bundleIdentifier isEqualToString:@"com.johnil.vvebo"] ||
            ![[bundle objectForInfoDictionaryKey:@"CFBundleShortVersionString"]
                isEqualToString:@"3.3.31"]) return;
        VVInstallNetworkCompatibility();
        if (!VVInstallPurchaseCompatibility(NSClassFromString(@"MMKV"))) {
            NSLog(@"[VVeboFix] Purchase compatibility unavailable: MMKV reader not found");
        }
    }
}
#endif
