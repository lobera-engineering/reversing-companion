#include <stdio.h>

#define unsigned_long_int unsigned long int

void greet_me()
{
    char name[200];
    register void *rsp asm ("%rsp");
    register void *rbp asm ("%rbp");
    unsigned_long_int size = ((rbp + 8 * 2) - rsp) / 8;
    

    printf("-----SZ: %lld | RSP: %llx | RBP: %llx ---------------\n",rsp,rbp);
    printf("[+] Canary value: %llx\n",*((unsigned_long_int*) (rbp-0x8)));
    printf("---------------------------------------------------------\n");
}

void greet_me_again()
{
    char name[200];
    register void *rsp asm ("%rsp");
    register void *rbp asm ("%rbp");
    unsigned_long_int size = ((rbp + 8 * 2) - rsp) / 8;
    

    printf("-----SZ: %lld | RSP: %llx | RBP: %llx ---------------\n",rsp,rbp);
    printf("[+] Canary value: %llx\n",*((unsigned_long_int*) (rbp-0x8)));
    printf("---------------------------------------------------------\n");

}


int main(int argc, char *argv[])
{
    greet_me();
    greet_me_again();
    return 0;  
}
