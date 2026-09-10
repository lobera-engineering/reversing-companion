#include <stdlib.h>
#include <stdio.h>
#include <string.h>
void unused(){
    char dummy1[10];
    char dummy2[10];
    strcpy(dummy1,dummy2);
}
void show_date(){
    system("/bin/date");
}
void greet_me()
{
    char name[200];
    show_date();
    printf("Enter your name:");
    gets(name);
    printf("hi %s !\n",name);
  
}
int main(int argc, char *argv[])
{
    greet_me();
    return 0;  
}
