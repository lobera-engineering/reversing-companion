#include <string.h>
#include <stdlib.h>
#include <stdio.h>
 
main() {    
   struct person {
     char name[30];
     char email[25];
     int age;
   };
 
   struct person *person1;


   person1 = (struct person*)
     malloc (sizeof(struct person));
   strcpy(person1->name, "Peter");
   strcpy(person1->email, "p@p.p");
   person1->age = 21;

   printf("Person data= %s, %s, and the age is: %d\n",
     person1->name, person1->email, person1->age);
   free(person1);


     getchar();
}
