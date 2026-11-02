#import <Foundation/Foundation.h>
#import <objc/runtime.h>

extern void VVInstallNetworkCompatibility(void);
extern BOOL VVInstallPurchaseCompatibility(Class);
extern NSURLRequest *VVTestRewrite(NSURLRequest *);
extern NSData *VVTestResponse(NSData *, NSString *);
extern Class VVTestProtocolClass(void);

static BOOL StorageInitialized;
static NSUInteger Passed;

@interface MMKV : NSObject
@property(nonatomic, copy) NSString *mmapID;
- (NSDate *)getDateForKey:(NSString *)key;
@end
@implementation MMKV
+ (void)initialize {
    if (self == objc_getClass("MMKV")) StorageInitialized = YES;
}
- (NSDate *)getDateForKey:(NSString *)key {
    return key ? [NSDate dateWithTimeIntervalSince1970:1000] : nil;
}
@end

static void Check(BOOL condition, NSString *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message.UTF8String);
        exit(1);
    }
    Passed++;
    printf("PASS: %s\n", message.UTF8String);
}

static NSData *JSONData(id value) {
    NSError *error;
    NSData *data = [NSJSONSerialization dataWithJSONObject:value options:0 error:&error];
    if (!data) {
        fprintf(stderr, "Invalid fixture: %s\n", error.description.UTF8String);
        exit(1);
    }
    return data;
}

static id Decode(NSData *data) {
    return [NSJSONSerialization JSONObjectWithData:data options:0 error:NULL];
}

int main(void) {
    @autoreleasepool {
        // Use exactly the production order: networking first, storage hook second.
        VVInstallNetworkCompatibility();
        Check(!StorageInitialized, @"Network setup does not initialize the storage class");
        Check(VVInstallPurchaseCompatibility(NSClassFromString(@"MMKV")),
              @"Purchase hook installs alongside the network hook");
        Check(!StorageInitialized, @"Combined setup preserves normal storage initialization timing");
        MMKV *store = [MMKV new];
        store.mmapID = @"com.johnil.vvebo";
        Check(StorageInitialized, @"Storage initializes on its first normal use");
        Check([[store getDateForKey:@"expireDate"] timeIntervalSince1970] > 31536000000.0,
              @"Purchase compatibility remains active with networking installed");
        Check([[store getDateForKey:@"lastSync"] timeIntervalSince1970] == 1000,
              @"Unrelated storage dates still use the original reader");

        NSURLRequest *request = [NSURLRequest requestWithURL:[NSURL URLWithString:
            @"https://api.weibo.cn/2/statuses/user_timeline?uid=42&max_id=7&count=20"]];
        NSURLRequest *rewritten = VVTestRewrite(request);
        NSURLComponents *parts = [NSURLComponents componentsWithURL:rewritten.URL resolvingAgainstBaseURL:NO];
        NSMutableDictionary *query = [NSMutableDictionary dictionary];
        for (NSURLQueryItem *item in parts.queryItems) query[item.name] = item.value;
        Check([parts.path isEqualToString:@"/2/profile/statuses/tab"], @"Timeline endpoint is rewritten");
        Check([query[@"since_id"] isEqualToString:@"7"] && query[@"max_id"] == nil,
              @"Timeline pagination converts max_id to since_id");
        Check([query[@"uid"] isEqualToString:@"42"] && [query[@"count"] isEqualToString:@"20"] &&
              [query[@"containerid"] isEqualToString:@"23041342_-_WEIBO_SECOND_PROFILE_WEIBO"],
              @"Timeline UID, container and unrelated query values are preserved");
        Check([request.URL.path isEqualToString:@"/2/statuses/user_timeline"],
              @"Original request is not modified");
        NSURLRequest *other = [NSURLRequest requestWithURL:[NSURL URLWithString:@"https://example.com/plain"]];
        Check(VVTestRewrite(other) == other, @"Unrelated requests pass through");

        NSData *profile = JSONData(@{@"cards": @[
            @{@"card_group": @[@{@"card_type": @9, @"mblog": @{@"id": @1, @"isTop": @YES}},
                                @{@"card_type": @8, @"mblog": @{@"id": @99}}]},
            @{@"card_type": @9, @"mblog": @{@"id": @2}}
        ], @"cardlistInfo": @{@"since_id": @"next-page"}});
        NSDictionary *converted = Decode(VVTestResponse(profile, @"https://api.weibo.cn/2/profile/statuses/tab"));
        NSArray *statuses = converted[@"statuses"];
        Check(statuses.count == 2 && [statuses[0][@"id"] isEqual:@1] && [statuses[1][@"id"] isEqual:@2],
              @"Grouped and flat profile cards become statuses; non-status cards are skipped");
        Check([statuses[0][@"label"] isEqualToString:@"置顶"], @"Pinned status label is retained");
        Check([converted[@"since_id"] isEqualToString:@"next-page"], @"Profile pagination survives conversion");
        NSData *fans = JSONData(@{@"cards": @[@{@"itemid": @"selffans"},
                                              @{@"itemid": @"INTEREST_PEOPLE2"}, @{@"itemid": @"normal"}],
                                  @"extra": @"keep"});
        NSDictionary *filtered = Decode(VVTestResponse(fans, @"https://api.weibo.cn/2/cardlist"));
        Check([filtered[@"cards"] count] == 2 && [filtered[@"extra"] isEqualToString:@"keep"],
              @"Fans recommendations are filtered while unrelated response fields survive");
        NSData *notFans = JSONData(@{@"cards": @[@{@"itemid": @"INTEREST_PEOPLE2"}]});
        Check(VVTestResponse(notFans, @"https://api.weibo.cn/2/cardlist") == notFans,
              @"Non-fans card lists pass through");
        NSData *invalid = [@"not-json" dataUsingEncoding:NSUTF8StringEncoding];
        Check(VVTestResponse(invalid, @"https://api.weibo.cn/2/profile/statuses/tab") == invalid,
              @"Invalid JSON safely falls back to the original response");
        Check(VVTestResponse(profile, @"https://example.com/plain") == profile,
              @"Unrelated response data passes through");

        Class protocol = VVTestProtocolClass();
        Check([protocol canInitWithRequest:request] && ![protocol canInitWithRequest:other],
              @"Protocol handles Weibo API requests and ignores unrelated requests");
        NSMutableURLRequest *handled = [request mutableCopy];
        [NSURLProtocol setProperty:@YES forKey:@"VVeboFixHandled" inRequest:handled];
        Check(![protocol canInitWithRequest:handled], @"Handled requests are excluded to prevent recursion");
        NSURLSessionConfiguration *normal = NSURLSessionConfiguration.defaultSessionConfiguration;
        NSURLSessionConfiguration *ephemeral = NSURLSessionConfiguration.ephemeralSessionConfiguration;
        Check([normal.protocolClasses containsObject:protocol] && [ephemeral.protocolClasses containsObject:protocol],
              @"Both session configurations contain the network protocol");
        NSUInteger count = 0;
        for (Class entry in normal.protocolClasses) if (entry == protocol) count++;
        Check(count == 1, @"A session configuration contains the protocol exactly once");
        ephemeral.protocolClasses = @[];
        Check(ephemeral.protocolClasses.count == 0, @"Inner sessions can clear protocols to avoid recursive loading");
        printf("Combined checks passed: %lu\n", (unsigned long)Passed);
    }
    return 0;
}
