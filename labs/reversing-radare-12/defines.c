#include <string.h>
#include <stdio.h>
 
#define SUM(x,y) x+y
#define MAX 10
 
int main() {
   int n1, n2;
 
   printf("VAL 1 = ");
   scanf("%d", &n1);
 
   printf("VAL 2 = ");
   scanf("%d", &n2);
 
   printf("SUM = %d\n", SUM(n1,n2));
   
   if(SUM(n1,n2)>MAX){
        printf("> MAX\n");      
   }
   getchar();
   getchar();
   return 0;
}
