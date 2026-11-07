#import <Cocoa/Cocoa.h>
#import <CoreBluetooth/CoreBluetooth.h>
static NSString *const ServiceID=@"4D8EA1D0-BE20-4101-8E12-000000000001";
static NSString *const ReadID=@"4D8EA1D0-BE20-4101-8E12-000000000002";
@interface Probe : NSObject <NSApplicationDelegate,CBPeripheralManagerDelegate>
@property(nonatomic,strong) NSWindow *window;
@property(nonatomic,strong) NSTextField *label;
@property(nonatomic,strong) CBPeripheralManager *manager;
@property(nonatomic,strong) CBMutableService *service;
@property(nonatomic,strong) NSMutableDictionary *report;
@property(nonatomic,strong) NSTimer *deadline;
@property BOOL requested;
@property BOOL published;
@property NSUInteger readCount;
@end
@implementation Probe
- (void)save:(NSString *)status {
 self.label.stringValue=status;
 self.report[@"status"]=status;
 self.report[@"timestamp"]=[[NSDate date] description];
 self.report[@"manager_state"]=@(self.manager.state);
 self.report[@"advertising"]=@(self.manager.isAdvertising);
 self.report[@"read_requests"]=@(self.readCount);
 NSData *data=[NSJSONSerialization dataWithJSONObject:self.report options:NSJSONWritingPrettyPrinted error:nil];
 NSString *dir=[[[NSBundle mainBundle] bundlePath] stringByDeletingLastPathComponent];
 [data writeToFile:[dir stringByAppendingPathComponent:@"普通BLE状态.json"] options:NSDataWritingAtomic error:nil];
}
- (void)applicationDidFinishLaunching:(NSNotification *)note {
 self.report=[@{@"service_uuid":ServiceID,@"characteristic_uuid":ReadID,@"local_name":@"BE201LE",@"test_value":@"BE201 BLE OK",@"records_peer_identifiers":@NO,@"records_user_payloads":@NO} mutableCopy];
 self.window=[[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,580,220) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable backing:NSBackingStoreBuffered defer:NO];
 self.window.releasedWhenClosed=NO;self.window.title=@"BE201 普通 BLE 链路测试";[self.window center];
 NSTextField *title=[NSTextField labelWithString:@"用 iPhone 的 nRF Connect 查找 BE201LE"];
 title.frame=NSMakeRect(24,166,540,24);[self.window.contentView addSubview:title];
 self.label=[NSTextField wrappingLabelWithString:@"等待开始。测试服务只返回 BE201 BLE OK。"];
 self.label.frame=NSMakeRect(24,76,530,70);[self.window.contentView addSubview:self.label];
 NSButton *start=[NSButton buttonWithTitle:@"开始广播" target:self action:@selector(start:)];start.frame=NSMakeRect(24,24,120,32);[self.window.contentView addSubview:start];
 NSButton *stop=[NSButton buttonWithTitle:@"停止测试" target:self action:@selector(stop:)];stop.frame=NSMakeRect(160,24,120,32);[self.window.contentView addSubview:stop];
 [self.window makeKeyAndOrderFront:nil];[NSApp activateIgnoringOtherApps:YES];
 [self save:@"等待开始。测试服务只返回 BE201 BLE OK。"];
 if([NSProcessInfo.processInfo.arguments containsObject:@"--advertise"])[self start:nil];
}
- (void)start:(id)sender {
 if(self.requested)return;self.requested=YES;self.readCount=0;
 self.deadline=[NSTimer scheduledTimerWithTimeInterval:600 target:self selector:@selector(stop:) userInfo:nil repeats:NO];
 if(!self.manager)self.manager=[[CBPeripheralManager alloc] initWithDelegate:self queue:dispatch_get_main_queue() options:@{CBPeripheralManagerOptionShowPowerAlertKey:@NO}];
 else if(self.manager.state==CBManagerStatePoweredOn)[self publish];
 [self save:@"等待蓝牙就绪；如系统询问蓝牙权限，请选择允许。"];
}
- (void)publish {
 if(!self.requested || self.published)return;
 CBMutableCharacteristic *characteristic=[[CBMutableCharacteristic alloc] initWithType:[CBUUID UUIDWithString:ReadID] properties:CBCharacteristicPropertyRead value:nil permissions:CBAttributePermissionsReadable];
 self.service=[[CBMutableService alloc] initWithType:[CBUUID UUIDWithString:ServiceID] primary:YES];self.service.characteristics=@[characteristic];
 self.published=YES;[self.manager addService:self.service];[self save:@"正在发布测试服务。"];
}
- (void)peripheralManagerDidUpdateState:(CBPeripheralManager *)peripheral {
 if(peripheral.state==CBManagerStatePoweredOn)[self publish];
 else {self.published=NO;[self save:[NSString stringWithFormat:@"蓝牙状态：%ld（5 为开启，3 为未授权，4 为关闭）",(long)peripheral.state]];}
}
- (void)peripheralManager:(CBPeripheralManager *)peripheral didAddService:(CBService *)service error:(NSError *)error {
 if(error){self.report[@"service_error_code"]=@(error.code);[self stop:nil];[self save:@"测试服务发布失败；错误编号已保存。"];return;}
 if(!self.requested){[peripheral removeAllServices];self.published=NO;return;}
 [peripheral startAdvertising:@{CBAdvertisementDataLocalNameKey:@"BE201LE",CBAdvertisementDataServiceUUIDsKey:@[[CBUUID UUIDWithString:ServiceID]]}];
}
- (void)peripheralManagerDidStartAdvertising:(CBPeripheralManager *)peripheral error:(NSError *)error {
 if(error){self.report[@"advertising_error_code"]=@(error.code);[self save:@"测试广播失败；错误编号已保存。"];return;}
 if(!self.requested){[peripheral stopAdvertising];return;}
 self.report[@"advertisement_start_callback"]=@YES;[self save:@"广播已启动：BE201LE。请在 iPhone 连接并读取以 0002 结尾的特征。"];
}
- (void)peripheralManager:(CBPeripheralManager *)peripheral didReceiveReadRequest:(CBATTRequest *)request {
 NSData *data=[@"BE201 BLE OK" dataUsingEncoding:NSUTF8StringEncoding];
 if(![request.characteristic.UUID isEqual:[CBUUID UUIDWithString:ReadID]]){[peripheral respondToRequest:request withResult:CBATTErrorRequestNotSupported];return;}
 if(request.offset>data.length){[peripheral respondToRequest:request withResult:CBATTErrorInvalidOffset];return;}
 request.value=[data subdataWithRange:NSMakeRange(request.offset,data.length-request.offset)];
 [peripheral respondToRequest:request withResult:CBATTErrorSuccess];self.readCount++;[self save:@"已收到真实 GATT 读取并返回 BE201 BLE OK。"];
}
- (void)stop:(id)sender {
 self.requested=NO;[self.deadline invalidate];self.deadline=nil;
 [self.manager stopAdvertising];[self.manager removeAllServices];self.service=nil;self.published=NO;
 [self save:@"测试已停止。"];
}
- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {[self stop:nil];return NSTerminateNow;}
- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {return YES;}
@end
int main(int argc,const char *argv[]){@autoreleasepool{NSApplication *app=[NSApplication sharedApplication];app.activationPolicy=NSApplicationActivationPolicyRegular;__attribute__((objc_precise_lifetime)) Probe *delegate=[Probe new];app.delegate=delegate;[app run];}return 0;}
