#include <stdio.h>
#include <string.h>

__asm__(".globl func\n\t"
        ".type func, @function\n\t"
        "func:\n\t"
        ".cfi_startproc\n\t"
        "sub %rbp, (%rdi)\n\t"
        "ret\n\t"
        ".cfi_endproc");

char *dummy = "sh";    

void greet_me()
{
    char name[200];
    printf("Enter your name:");
    gets(name);
    printf("hi %s !\n",name);
  
}
int main(int argc, char *argv[])
{
    greet_me();
    return 0;  
}
