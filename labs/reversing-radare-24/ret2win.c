#include <stdlib.h>
#include <stdio.h>
void unused_shell_func(){
    system("/bin/sh");
}
void greet_me()
{
    char name[200];
    
    printf("Enter your name:");
    gets(name);
    printf("Hi there %s !!\n",name);
  
}
int main(int argc, char *argv[])
{
    
    greet_me();
    return 0;  
}
