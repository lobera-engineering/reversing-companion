#include <stdio.h>
#include <arpa/inet.h>

int main(int argc, char **argv) {

int retval;
   struct in_addr addrptr;
   
   memset(&addrptr, '\0', sizeof(addrptr));
   retval = inet_aton("68.178.157.132", &addrptr);
   exit(0);
}
