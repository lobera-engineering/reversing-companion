#include <stdio.h>
void show_date(){
    system("/bin/date");
}
void greet_me()
{
    char name[200];
    printf("Enter your name:");
    gets(name);
    printf("%s !it is you again  !!! oh my gosh",name);
  
}
int main(int argc, char *argv[])
{
    show_date();
    greet_me();
    return 0;  
}
