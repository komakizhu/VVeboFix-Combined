#import <Foundation/Foundation.h>
#import <objc/message.h>
#import <objc/runtime.h>
#include <pthread.h>

typedef NSDate *(*VVDateGetter)(id, SEL, NSString *);
static VVDateGetter VVOriginalDateGetter;
static pthread_mutex_t VVInstallationLock = PTHREAD_MUTEX_INITIALIZER;

static NSDate *VVCompatibleDate(id store, SEL selector, NSString *key) {
    SEL identifierSelector = sel_registerName("mmapID");
    if ([key isKindOfClass:NSString.class] && [key isEqualToString:@"expireDate"] &&
        [store respondsToSelector:identifierSelector]) {
        NSString *identifier = ((id (*)(id, SEL))objc_msgSend)(store, identifierSelector);
        if ([identifier isEqualToString:@"com.johnil.vvebo"]) {
            return NSDate.distantFuture;
        }
    }
    return VVOriginalDateGetter(store, selector, key);
}

static BOOL VVInstallCompatibility(Class storeClass) {
    if (!storeClass) return NO;
    SEL marker = sel_registerName("vv_local_purchase_compat_installed");
    // ARC retains the expression used by @synchronized. Retaining a Class can
    // run +initialize here, before UIApplicationMain. This bundled MMKV version
    // accesses UIApplication.sharedApplication in +initialize, so use a C lock.
    pthread_mutex_lock(&VVInstallationLock);
    BOOL installed = NO;
    do {
        if (objc_getAssociatedObject(storeClass, (const void *)marker)) {
            installed = YES;
            break;
        }
        Method method = class_getInstanceMethod(storeClass, sel_registerName("getDateForKey:"));
        if (!method || method_getNumberOfArguments(method) != 3 ||
            method_getTypeEncoding(method)[0] != '@') break;
        VVOriginalDateGetter = (VVDateGetter)method_getImplementation(method);
        method_setImplementation(method, (IMP)VVCompatibleDate);
        objc_setAssociatedObject(storeClass, (const void *)marker, @YES,
                                 OBJC_ASSOCIATION_RETAIN_NONATOMIC);
        installed = YES;
    } while (NO);
    pthread_mutex_unlock(&VVInstallationLock);
    return installed;
}

#if VV_COMPAT_TESTING
BOOL VVInstallCompatibilityForTests(Class storeClass) {
    return VVInstallCompatibility(storeClass);
}
#else
__attribute__((constructor))
static void VVLoadPurchaseCompatibility(void) {
    @autoreleasepool {
        NSBundle *bundle = NSBundle.mainBundle;
        if (![bundle.bundleIdentifier isEqualToString:@"com.johnil.vvebo"] ||
            ![[bundle objectForInfoDictionaryKey:@"CFBundleShortVersionString"]
                isEqualToString:@"3.3.31"]) return;
        if (VVInstallCompatibility(NSClassFromString(@"MMKV"))) {
            NSLog(@"[VVeboPurchaseCompat] local purchase compatibility enabled");
        } else {
            NSLog(@"[VVeboPurchaseCompat] expected MMKV date reader unavailable");
        }
    }
}
#endif
