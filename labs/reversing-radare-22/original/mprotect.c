#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>
#include <signal.h>
void greet_me(){
    char name[200];
    gets(name);
    printf("Hi there %s !!\n",name);
}
int main(int argc, char *argv[]){
    int pagesize = sysconf(_SC_PAGE_SIZE);
    printf("Pagesize:%d\n",pagesize);
    if(mprotect(0x7ffffffde000,pagesize,0x7)==0)
    {
        printf("[i] Operation successfull\n");
        printf("[i] Memory region:  0x7ffffffe0000 to %lx has been      set to r-w-x\n",0x7ffffffe0000+pagesize);
    }
    else
        printf("[!] Operation failed\n");
    greet_me();
    
    return 0;  
}
