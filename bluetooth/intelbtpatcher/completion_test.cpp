#include <cstdint>
#include <cassert>
#include <thread>
#include <cstdio>
using IOReturn=int;
using Action=void(*)(void*,void*,IOReturn,uint32_t);
struct IOUSBHostCompletion{void *owner; Action action; void *parameter;};
#include "AddressCompletion.hpp"
#include "NativeAddressGuard.hpp"
static be201address::Guard guard={};
static bool useGuard=true;
struct Owner {unsigned count=0; int status=0; uint32_t bytes=0; void *parameter=nullptr;};
static void original(void *o,void *p,int status,uint32_t bytes){auto *x=(Owner*)o;x->count++;x->status=status;x->bytes=bytes;x->parameter=p;}
static void finished(uint64_t ticket,int status,uint32_t bytes,bool callback){
 if(useGuard){if(callback&&status==0&&bytes==9)guard.accepted(ticket,true,true,bytes);else guard.rejected(ticket);}
}
static BE201AddressCompletion *make(Owner &o,void *parameter,uint64_t ticket){auto *x=new BE201AddressCompletion;x->original={&o,original,parameter};x->ticket=ticket;x->finished=finished;return x;}
int main(){
 assert(guard.bind(201));int parameter=42;
 {Owner o;auto *x=make(o,&parameter,guard.invalidate());auto c=x->wrapped();x->submitted(0);assert(o.count==0&&!guard.preserve(201));c.action(c.owner,c.parameter,0,9);assert(o.count==1&&o.parameter==&parameter&&o.status==0&&o.bytes==9&&guard.preserve(201));}
 {Owner o;auto *x=make(o,&parameter,guard.invalidate());auto c=x->wrapped();c.action(c.owner,c.parameter,0,9);x->submitted(0);assert(o.count==1&&guard.preserve(201));}
 {Owner o;auto *x=make(o,&parameter,guard.invalidate());x->submitted(-1);assert(o.count==0&&!guard.preserve(201));}
 for(int status:{-1,0}){Owner o;auto *x=make(o,&parameter,guard.invalidate());auto c=x->wrapped();x->submitted(0);c.action(c.owner,c.parameter,status,8);assert(o.count==1&&o.status==status&&o.bytes==8&&!guard.preserve(201));}
 {Owner o;auto *x=make(o,&parameter,guard.invalidate());auto c=x->wrapped();x->submitted(0);guard.invalidate();c.action(c.owner,c.parameter,0,9);assert(o.count==1&&!guard.preserve(201));}
 {Owner a,b;auto *x=make(a,&parameter,guard.invalidate());auto cx=x->wrapped();x->submitted(0);auto *y=make(b,&parameter,guard.invalidate());auto cy=y->wrapped();y->submitted(0);cy.action(cy.owner,cy.parameter,0,9);cx.action(cx.owner,cx.parameter,-1,0);assert(guard.preserve(201)&&a.count==1&&b.count==1);}
 useGuard=false;
 for(unsigned i=0;i<1000;i++){Owner o;auto *x=make(o,&parameter,2);auto c=x->wrapped();std::thread t([c]{c.action(c.owner,c.parameter,0,9);});x->submitted(0);t.join();assert(o.count==1&&o.parameter==&parameter);}
 puts("PASS: actual production completion wrapper; delayed/immediate callbacks, submission error, abort/short transfer, reset and stale outcome, exact callback forwarding, 1000 concurrent return/callback lifetimes (ASan/UBSan).");
}
